# TPP Binary Encoding

Reverse-engineered from Cube Voyager 6.5.1 x64 output.
Validated bit-exact against Cube CSV dumps across 81 skim files (1.1 billion cells, 0 mismatches).

## What is a TPP file?

A TPP (TranPlan Plus) file is a proprietary binary format used by Cube Voyager
to store square origin-destination matrices. Rows and columns are numbered zones (e.g. 1–1475), and each cell holds a number like travel time or distance.

A single TPP file can contain multiple named tables (e.g. `TIMEDA`,
`DISTDA`, `BTOLLDA`) that all share the same zone system. The values are
decimal numbers (like `12.45` minutes), but TPP stores them as integers
with a separate precision byte that says where to put the decimal point,
this saves space compared to storing full floating-point numbers.

The file has two parts: a **header** (metadata) and **data blocks** (the
actual matrix values, compressed).

## Background: Bytes encoded numbers

### Bytes and byte order (little-endian)

A byte can hold values 0–255. To store bigger numbers, you chain multiple
bytes together. Each byte position is worth 256× more than the one before
it (just like each digit in decimal is worth 10× more):

```
Decimal:  each digit is worth 10× more     →  ones, tens, hundreds, ...
Bytes:    each byte is worth 256× more     →  ×1, ×256, ×65536, ×16777216, ...
                                               (256⁰, 256¹, 256², 256³)
```

"Little-endian" means the bytes are stored smallest part first. It's like
writing "five hundred" as "0, 0, 5" instead of "5, 0, 0". For example, to
store the number 70,000 as 4 bytes:

```
70000 = 112×1 + 17×256 + 1×65536 + 0×16777216

Normal (big-endian):   00 01 11 70     →  leftmost byte is the biggest part
Little-endian:         70 11 01 00     →  leftmost byte is the smallest part
                       ↑   ↑   ↑
                      112  17   1
                       └───┴───┴── 112 + (17 × 256) + (1 × 65536) = 70,000
```

TPP uses little-endian throughout because that's the native byte order
on x86 (Intel/AMD) processors (it's what Windows uses internally).

### Splitting numbers into lo and hi bytes

TPP splits each value into separate bytes called **lo** (low) and **hi**
(high). A single byte can only hold 0–255, so to store a bigger number
you use two bytes:

```
lo byte = the "ones" part      (×1,   i.e. 0–255)
hi byte = the "256s" part      (×256, i.e. 0–65280 in steps of 256)

value = hi × 256 + lo
```

For example, the number 1245 split into two bytes:

```
1245 ÷ 256 = 4 remainder 221
         → hi = 4, lo = 221
         → check: 4 × 256 + 221 = 1245 ✓
```

For very large values (above 65535), a third **mid byte** is added
between lo and hi, giving three "digits" in base-256:

```
value = hi × 65536 + mid × 256 + lo
```

### Precision (the decimal point)

Instead of storing `12.45` as a floating-point number, TPP stores the
integer `1245` and a precision byte that says "divide by 100":

```
12.45  →  stored as integer 1245, with precision byte = 0x20 (meaning ÷100)
         1245 = hi × 256 + lo = 4 × 256 + 221
         final value = 1245 ÷ 100 = 12.45
```

The precision byte's upper nibble picks a power-of-10 divisor:

| Precision byte | Divide by | Example |
|----------------|-----------|---------|
| `0x00` | 1 | `1245 ÷ 1 = 1245.0` |
| `0x10` | 10 | `1245 ÷ 10 = 124.5` |
| `0x20` | 100 | `1245 ÷ 100 = 12.45` ← most common |
| `0x30` | 1,000 | `1245 ÷ 1000 = 1.245` |
| `0x40` | 10,000 | `1245 ÷ 10000 = 0.1245` |
| `0x50`–`0x90` | 10^5 – 10^9 | (rarely used) |

Each cell in a row can have a **different** precision byte, though in
practice most cells in a table use the same one (typically `0x20`).

### The full pipeline

Putting it all together, going from raw bytes to a decimal value:

```
bytes on disk → lo, hi (and maybe mid) → integer → ÷ precision → float

Example:  lo=0xDD, hi=0x04, prec=0x20
          integer = 4 × 256 + 221 = 1245
          float   = 1245 ÷ 100 = 12.45
```

## File Layout

```
┌─────────────────────────────────────────┐
│  Header  (metadata about the matrices)   │
│    PAR record  →  how many zones         │
│    MVR record  →  table names            │
│    ROW record  →  "header is done"       │
├─────────────────────────────────────────┤
│  Data blocks  (the actual numbers)       │
│    One block per row per table,          │
│    each compressed independently         │
└─────────────────────────────────────────┘
```

## Header

The header is a sequence of **records**. Each record starts with a 4-byte
little-endian length, followed by that many bytes of ASCII text.

The record names are legacy abbreviations from TranPlan:

| Record | Stands for | Purpose |
|--------|-----------|---------|
| `PAR`  | **Par**ameters | Key-value pairs like `Zones=1475`. Tells us the matrix dimensions. |
| `MVR`  | **M**atrix **V**a**r**iable | Lists the table names (e.g. `TIMEDA`, `DISTDA`), separated by NUL (`\0`) bytes. Each name can optionally have `=D` appended to specify decimal places. |
| `ROW`  | **Row** (sentinel) | Contains just the text `ROW`. Signals "the header is finished, data blocks start next." |

**Example** (conceptual): a file with 1475 zones and 3 tables would have:
```
[PAR] "PAR Zones=1475"
[MVR] "MVR\0TIMEDA\0DISTDA\0BTOLLDA\0"
[ROW] "ROW"
```

## Data Blocks

After the header, the rest of the file is a sequence of data blocks. Each
block stores **one row of one table** — for example, "row 42 of TIMEDA"
(meaning: the travel time from zone 42 to every other zone).

### Block Envelope (5 bytes)

Every block starts with a fixed 5-byte header:

```
row  : 2 bytes (u16, little-endian)  — which zone row (1-based)
tbl  : 1 byte  (u8)                  — which table (1-based index)
blen : 2 bytes (u16, little-endian)  — payload size + 2
```

The payload immediately follows. Its 3rd byte (offset `[2]`) is the
**type byte**, which tells you how the numbers in this row are encoded.

### Block Types

Different rows need different encodings depending on their data. A transit
skim row where zone 42 can't reach most zones is mostly zeros (sparse),
while a highway skim row where zone 42 can reach everywhere has values in
every cell (dense).

| Type byte | Name | When used | How values are stored |
|-----------|------|-----------|----------------------|
| `0x00` | Zero row | Row is entirely zeros | No data at all — skip it |
| `0x40` | Sparse hi-only | All non-zero values are exact multiples of 256 | One compressed section of "high bytes" only. Value = `hi × 256` |
| `0x80` | Sparse lo-only | All non-zero values fit in 0–255 | One compressed section of "low bytes". Value = `lo` |
| `0xC0` | Sparse 2-byte | Integer values up to 65535 | Two compressed sections (lo bytes, then hi bytes). Value = `hi × 256 + lo` |
| `0xC8` | 2-byte + precision | Decimal values (most common) | Three sections (lo, hi, precision). Value = `(hi × 256 + lo) ÷ divisor` |
| `0xE8` | 3-byte + precision | Large decimal values | Four sections (lo, mid, hi, precision). Value = `(hi × 65536 + mid × 256 + lo) ÷ divisor` |

### Sparse vs Dense within 0xC8 and 0xE8

These two types can encode data in **sparse** or **dense** mode, chosen
per-row based on whichever is smaller:

- **Sparse** (`zone_field & 0x8000`): each byte lane (lo, hi, prec) is
  compressed with a codec optimised for mostly-zero data.
- **Dense** (`zone_field < 0x8000`): the lo bytes start as raw
  (uncompressed) data for the first `n_raw` zones, then the rest is
  compressed. Hi and prec bytes are fully compressed.

`zone_field` is a 2-byte value at payload offset `[3..4]`. Its high bit
is the sparse/dense flag; the remaining 15 bits give `n_raw` (number of
uncompressed lo bytes in dense mode).

## Compression

TPP uses two simple compression schemes. Both work on **byte streams** —
sequences of single bytes (0–255). The idea is always the same: if you have
a long run of the same byte (like 500 zeros in a row), store "repeat 0x00
× 500" instead of writing out all 500 bytes.

### Block Codec (used in dense mode)

Each instruction is a 2-byte header `(count, mode)`, optionally followed by data:

| Pattern | What it does |
|---------|-------------|
| `mode` has high bit set (`& 0x80`) | **Run-length**: read the next byte, repeat it `count + (mode & 0x7F) × 256` times |
| `mode == 0x00` | **Literal**: copy the next `count` bytes as-is |
| `count < 0x80` *(precision lane only)* | **Shorthand run-length**: repeat the `mode` byte itself `count` times |
| Otherwise | **Big literal**: copy the next `(count + mode × 256) & 0x7FFF` bytes |

### Sparse Codec (used in sparse mode, and for hi/prec in 0xE8 dense)

Same idea, slightly different rules:

| Pattern | What it does |
|---------|-------------|
| `mode == 0x00` | **Literal**: copy the next `count_byte` bytes |
| `mode` has high bit set (`& 0x80`) | **Run-length**: repeat the next byte `(count_byte + mode × 256) & 0x7FFF` times |
| Otherwise | **Big literal**: copy the next `(count_byte + mode × 256) & 0x7FFF` bytes |

Both codecs always produce exactly `zones` output bytes. Any unwritten
trailing positions default to zero.

## Decoding Algorithm

```
1. Open the file and read header records until "ROW":
     - From PAR: extract zones (e.g. 1475)
     - From MVR: extract table names (e.g. ["TIMEDA", "DISTDA", ...])

2. Read all remaining bytes into memory (for speed).

3. Walk through data blocks:
     a. Read the 5-byte envelope → row number, table index, payload size
     b. Look at the type byte (payload[2])
     c. Based on the type, decompress the byte lanes:
        - Sparse types: decode lo (and hi, mid, prec) with sparse codec
        - Dense types:  read raw lo bytes + decompress the rest with block codec
     d. Reassemble the floating-point value:
            value = (hi × 256 + lo) ÷ precision_divisor
        or for wide blocks:
            value = (hi × 65536 + mid × 256 + lo) ÷ precision_divisor
     e. Store the resulting 1×zones float64 array into the output matrix

4. Result: a dictionary of {table_name: zones×zones numpy array}
```
