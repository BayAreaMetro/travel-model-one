# Cube Voyager `.net` Binary Encoding

Reverse-engineered from highway networks written by Cube Voyager 6.5.1 x64
and 6.4.5 x86. This document covers the read-only native implementation:
container metadata, speed/capacity lookup tables, node records, and link
records. Writing `.net` files remains outside scope.

Unlike TPP matrices, the `.net` files examined here are not compressed. They
are streams of little-endian, length-prefixed sections. Values inside `NOD`
and `LNK` use compact tagged encodings, but those encodings are not
compression streams and each record can be decoded independently.

## File layout

The verified files contain these sections in order:

```text
NET  plaintext producer/version/date banner
ID=  network identifier
PAR  network counts and other parameters
SPD  speed lookup table
CAP  capacity lookup table
NVR  node-variable dictionary
LVR  link-variable dictionary
NOD  node records
LNK  link records
END  end marker
```

`read_net()` decodes every section carrying network semantics. The narrower
`read_net_nodes()` and `read_net_links()` entry points deliberately skip
unrequested record or lookup payloads.

### Outer section envelope

Every section has the same envelope:

```text
offset +0  u32le total_length
offset +4  payload[total_length - 4]
```

`total_length` includes its own four-byte prefix. This is easy to get wrong:
the first section of the primary fixture starts with `4d 00 00 00`, so its
total length is 77 bytes and its payload is 73 bytes, not 77 bytes.

The primary loaded-network fixture has this layout. Offsets point to the
four-byte length prefix and lengths are total section lengths.

| Offset | Length | Payload marker |
|-------:|-------:|----------------|
| 0 | 77 | `NET` |
| 77 | 8 | `ID=` |
| 85 | 70 | `PAR` |
| 155 | 1,545 | `SPD` |
| 1,700 | 1,564 | `CAP` |
| 3,264 | 51 | `NVR` |
| 3,315 | 1,980 | `LVR` |
| 5,295 | 353,044 | `NOD` |
| 358,339 | 18,829,100 | `LNK` |
| 19,187,439 | 8 | `END` |

The final eight bytes are exactly:

```text
08 00 00 00 45 4e 44 00
\-----------/ E  N  D \0
 total = 8
```

The end of `END` must be the end of the file. Offsets and section sizes vary
with the dictionaries and records, so readers must walk the envelopes rather
than hard-code the example offsets.

## Metadata

### `NET`, `ID=`, and `PAR`

The `NET` payload is a NUL-terminated ASCII banner. For example:

```text
NET PGM=HWYNET (v.07/10/2023 [6.5.1 x64]) DATE=...
```

The `ID=` payload is also NUL-terminated ASCII. `PAR` starts with `PAR ` and
contains space-separated `key=value` tokens followed by NUL padding:

```text
PAR Zones=1475 Nodes=39030 Links=33953 NodeRecs=14192
```

The similarly named counts have different meanings:

- `Zones=1475` is the modeled-zone count.
- `Nodes=39030` is the highest node number, not the number of node records.
- `NodeRecs=14192` is the number of records in `NOD`.
- `Links=33953` is the number of link records.

Node numbers therefore need not be contiguous. Use `NodeRecs`, not `Nodes`,
when validating how many node records were read.

### `NVR` and `LVR` variable dictionaries

The variable dictionaries are NUL-delimited ASCII. Their first item contains
the dictionary type and field count; exactly that many descriptors follow:

```text
NVR 6\0N\0X\0Y\0GGFARE\0PROJ=019\0PBA2050_RTP_ID=001\0
```

A descriptor without a suffix is numeric. A descriptor ending in `=NNN` is a
string, and the three decimal digits give its declared maximum width. The
suffix is metadata and is removed from the returned field name. Thus the
example dictionary describes:

| Descriptor | Name | Kind | Declared width |
|------------|------|------|----------------|
| `N` | `N` | numeric | none |
| `PROJ=019` | `PROJ` | string | 19 |
| `PBA2050_RTP_ID=001` | `PBA2050_RTP_ID` | string | 1 |

Record values do not repeat their names. A node record contains one value per
`NVR` descriptor, in dictionary order.

## `SPD` and `CAP` lookup tables

Cube stores the built-in speed-class and capacity-class tables separately from
the links that reference them. Each table contains 891 unsigned values in
lane-major order: nine lane rows by 99 classes.

After the four-byte `SPD\0` or `CAP\0` marker, the observed body is:

```text
u8      seed/default       SPD=1, CAP=20
bytes4  06 20 80 c0        observed codec header
u16le   value_count        891
u8[891] low bytes
bytes[] sparse stream producing exactly 891 high bytes
```

The exact meaning of every header flag has not been independently established,
so the reader accepts the verified header rather than guessing at variants.
The sparse high-byte stream uses these instructions:

```text
read low_count, mode
run_length = low_count | ((mode & 0x7f) << 8)

if mode & 0x80:
    read one byte and repeat it run_length times
else:
    copy the next run_length literal bytes
```

Zero-length runs, output beyond 891 bytes, truncated runs, and bytes remaining
after the 891st output byte are errors. Combine corresponding low and high
bytes as:

```text
stored = low | (high << 8)
```

`CAP` returns `stored` as integer vehicles per lane per hour. `SPD` stores
one decimal place and returns `stored / 10`. The public tables use
`table[lanes - 1][class - 1]`; capacity values are not multiplied by the lane
count. Cube's `CAPACITYFOR` performs that multiplication when applying the
lookup.

## `NOD` records

The outer `NOD` payload starts with the four bytes `NOD\0`. A sequence of node
records follows immediately.

### Record envelope

Each node record begins with a one- or two-byte payload length:

```text
read b0

if b0 < 0x80:
    prefix_length = 1
    payload_length = b0
else:
    read b1
    prefix_length = 2
    payload_length = ((b0 & 0x7f) << 8) | b1
```

The payload length excludes the one- or two-byte prefix. For example, `16`
means 22 payload bytes. The general two-byte form `82 0f` means
`(2 * 256) + 15 = 527` payload bytes. All node records in the two verified
fixtures use the short form; both envelope forms are also structurally
verified while walking `LNK` records.

Decode exactly the number and kinds of fields declared by `NVR`, then require
the decoder to be exactly at the record boundary. After `NodeRecs` records,
the decoder must be exactly at the end of the `NOD` section.

## Numeric values

Every numeric field begins with a tag. Small non-negative integers use the
tag byte itself; larger integers, fixed-point decimals, and floating-point
values carry bytes after the tag.

| Tag | Following bytes | Decoded value |
|-----|-----------------|---------------|
| `00`-`3f` | none | `tag` |
| `48`-`4f` | `u8 b` | `((tag & 7) << 8) | b` |
| `50`-`57` | `u16le n` | `((tag & 7) << 16) | n` |
| `88` | `f64le x` | `x` |
| `90`-`9f` | 1-4 unsigned little-endian bytes | fixed-point value described below |
| `a4` | `f32le x` | `x` |

For a fixed-point tag `t` in `90`-`9f`:

```text
width          = (t & 0x03) + 1
decimal_places = 1 + ((t - 0x90) >> 2)
raw            = unsigned little-endian integer in the next `width` bytes
value          = raw / (10 ** decimal_places)
```

For example, `95 d2 04` has width 2 and two decimal places. The raw integer is
`0x04d2 = 1234`, so the decoded value is `12.34`.

### Packed-integer thresholds

The node numbers demonstrate the canonical transitions between compact
integer forms:

| Value | Bytes | Calculation |
|------:|-------|-------------|
| 63 | `3f` | inline tag |
| 64 | `48 40` | `(0 << 8) | 0x40` |
| 73 | `48 49` | `(0 << 8) | 0x49` |
| 255 | `48 ff` | `(0 << 8) | 0xff` |
| 256 | `49 00` | `(1 << 8) | 0x00` |
| 2,047 | `4f ff` | `(7 << 8) | 0xff` |
| 2,048 | `50 00 08` | `(0 << 16) | 0x0800` |
| 39,030 | `50 76 98` | `(0 << 16) | 0x9876` |

The byte pair for node 73 is `48 49`. The superficially similar `49 00`
encodes 256.

### Floating-point example

Node 1's `X` value is stored as:

```text
88 00 00 00 80 12 e0 20 41
^^ \----------------------/
tag       f64le bytes
```

Interpreting the eight bytes after `88` as an IEEE-754 little-endian double
gives `552969.25`.

No signed packed-integer encoding was needed or identified in the verified
files. Negative values can still be represented by the floating-point forms.
Unknown numeric tags are errors rather than values to guess at.

## String values

Strings are ASCII byte strings with a tagged length:

| Tag | Following bytes | String length |
|-----|-----------------|---------------|
| `c0`-`fe` | string bytes | `tag - 0xc0` (0-62) |
| `ff` | `u8 length`, then string bytes | the explicit length byte |

The bytes are not padded to the width from `NVR` or `LVR`. The declared width
is a schema constraint, while the record carries the actual value length.

Examples:

```text
c0                         -> ""
c3 41 42 43                -> "ABC"
c9 43 43 5f 30 37 30 30 30 39
                           -> "CC_070009" (9 bytes)
ff 3f <63 ASCII bytes>     -> a 63-byte string
```

Node 20505 contains the 19-byte value `SF_070027_Completed`, encoded as tag
`d3` (`0xc0 + 19`) followed by those 19 ASCII bytes. Its other string field is
empty and is encoded as `c0`.

## Worked node records

Node 1 begins:

```text
16 | 01 | 88 <8-byte X> | 88 <8-byte Y> | 00 | c0 | c0
```

The `16` envelope declares 22 payload bytes:

```text
1-byte N + 9-byte X + 9-byte Y + 1-byte GGFARE
           + 1-byte PROJ + 1-byte PBA2050_RTP_ID = 22
```

At the first packed-integer threshold, node 73 begins:

```text
17 | 48 49 | 88 <8-byte X> | 88 <8-byte Y> | 00 | c0 | c0
```

Its two-byte node number makes the payload 23 bytes, hence `17`. Node 39030
uses the three-byte number `50 76 98`, so its otherwise empty-string record
starts with payload length `18` (24 bytes).

## `LNK` records

The `LNK` payload starts with `LNK\0`, followed by exactly `PAR Links`
records. Links use the same record envelope and numeric/string codecs as
nodes. Decode one value for every `LVR` descriptor in dictionary order and
require exact consumption of both each record and the entire section.

`A` and `B` are required numeric fields. Both must decode as integers within
`1..PAR Nodes`. A full `read_net()` additionally requires both endpoints to
exist among the decoded `NOD` records. Parallel links are valid and are not
deduplicated.

The freeflow fixture directly exercises the envelope transition:

| Payload bytes | Prefix | Meaning |
|--------------:|--------|---------|
| 127 | `7f` | one-byte envelope |
| 128 | `80 80` | two-byte envelope |

The loaded fixture's first link begins `82 0f 01 50 3f 1d ...`: `82 0f`
declares 527 payload bytes, then `A=1` and `B=7487`. Its 33,953 link
payloads range from 242 to 850 bytes and all use two-byte envelopes. The
freeflow fixture has the same link count with payloads from 101 to 262 bytes,
using both envelope forms.

## Decoding algorithm

```text
1. Walk outer sections using each u32le total length.
2. Parse NET, ID=, and PAR metadata.
3. Parse the NVR and LVR dictionaries.
4. For a full read, decode SPD and CAP into 9-by-99 tables.
5. Enter NOD after its four-byte "NOD\0" marker.
6. Repeat PAR["NodeRecs"] times:
     a. Decode the record envelope.
     b. Decode one numeric or string value per NVR descriptor, in order.
     c. Require exact consumption of the declared record payload.
7. Require exact consumption of NOD.
8. Seek to LNK and repeat PAR["Links"] times:
     a. Read one record without buffering the entire section.
     b. Decode one value per LVR descriptor and validate A/B.
     c. Require exact record and section consumption.
9. Require END to be the final section and exact file EOF.
```

The public entry points are:

- `read_net_nodes(path)`: metadata and materialized node dictionaries.
- `iter_net_links(path)`: a record-at-a-time link iterator.
- `read_net_links(path)`: metadata and materialized link dictionaries.
- `read_net(path)`: lookup tables, nodes, and links, including endpoint
  membership validation.

Dictionary insertion order follows NVR/LVR. Numeric values are Python `int`
or `float`; strings are Python `str`, and an encoded `c0` is returned as
`""`. Materializing 33,953 links with 216 fields requires roughly 288 MiB for
the link dictionaries alone, so consumers that do not need random access
should prefer `iter_net_links()`. The API launches no Cube process and
requires no Cube/Bentley license.

## Validation evidence

The primary fixture is `avgload5period.net`, written by Voyager 6.5.1 x64.
Its 14,192 node rows and all six `N,X,Y,GGFARE,PROJ,PBA2050_RTP_ID` columns
were compared in strict row and column order with Cube's CS1 export. Every
cell matched after accounting for the CS1 presentation rules:

- Cube formats node coordinates to five decimal places and removes trailing
  zeroes; validation applies the same formatting to decoded floats.
- Cube renders an empty string as the literal field `' '`; validation maps
  only that exact representation to the native empty string `""`.

This is a textual CS1-oracle comparison, not a claim that a five-decimal CSV
can prove equality of every bit in an on-disk `f64`. The reader returns the
value obtained directly from the IEEE-754 bytes.

For the cross-version check, a fresh `freeflow_nodes.csv` oracle was exported
from `freeflow.net` by Cube itself (`PGM=NETWORK`, `FORMAT=CS1`) through the
interactive-session runner. All 14,192 rows and 85,152 cells matched with
zero discrepancies. Together, the two oracle comparisons checked 170,304
cells. The two independently generated CSV files have the same SHA-256,
`11524a7220ac22eaef48b1b1c0690ebf27e152adf5f60556a9c45f7d62ad4e29`,
because the node data are the same.

The `NOD` outer section in the 6.4.5 x86 `freeflow.net` is likewise
byte-for-byte identical to the primary fixture's 353,044-byte `NOD` section:

```text
SHA-256  2cf942d232093549bd44cc54b85e9a7ccdd10152d2cd6a1ce71d03ae5215fff7
```

The files still exercise different container traversal: the 6.5.1 network has
216 link variables and places `NOD` at offset 5,295, while the 6.4.5 network
has 86 link variables and places it at offset 4,095.

The loaded network's link result was compared exhaustively with Cube's
`avgload5period_links.csv` oracle: all 216 headers, 33,953 rows, and
7,333,848 cells matched in exact dictionary/record order. Those cells comprise
7,130,130 numeric and 203,718 string values. Cube's CS1 output rounds floats to
five places using decimal half-up rounding (not Python's default half-even
rounding) and wraps strings containing spaces in apostrophes; the validator
normalizes only those presentation rules.

The freeflow link block independently decoded 33,953 records with 86 fields,
or 2,919,958 values, and consumed every record and the LNK section exactly.
Across both fixtures, all 135,812 endpoint values decoded as integers,
resolved to NOD records, and fell within `1..PAR Nodes`.

The SPD and CAP codec was also walked over all 127 `.net` files under the
local test corpus with zero errors. All 127 copies happened to be byte
identical, so this validates the implemented codec but represents only one
lookup-header variant. Decoded values were independently compared with the
model's `SPDCAP` statements: all 891 capacity cells and every explicitly set
speed class matched. The dimensions, one-decimal speed storage, and per-lane
capacity semantics agree with the Cube Voyager reference guide.

## Known limits

- This is a reverse-engineered format, not an official Bentley specification.
- Fixed-point tags `90`-`9f` occur in the fixtures. The apparent continuation
  `a0`-`a3` has not been observed and is rejected rather than guessed.
- No signed compact-integer tag has been identified.
- Strings in the verified dictionaries and records are ASCII.
- Only the observed SPD/CAP header is accepted; other header variants are
  rejected explicitly rather than inferred.
- Full reads materialize nodes and links for convenience. Use the link iterator
  when the roughly 288 MiB link-object cost of the primary fixture is unwanted.
- A writer is explicitly out of scope.
