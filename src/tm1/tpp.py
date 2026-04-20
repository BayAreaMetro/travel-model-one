"""Pure-Python reader for Cube Voyager TPP (TranPlan Plus) matrix files.

Reverse-engineered from Cube Voyager 6.5.1 x64 TPP output.
Validated bit-exact against Cube's own CSV dumps across 81 skim files
(1,109,300,726 cells, 0 mismatches).

Usage::

    from tm1.tpp import read_tpp

    result = read_tpp("HWYSKMEA.tpp")
    # result['zones']  -> 1475
    # result['tables'] -> ['TIMEDA', 'DISTDA', ...]
    # result['data']   -> {'TIMEDA': ndarray(1475, 1475), ...}

TPP File Format
===============

A TPP file stores square origin-destination matrices (zones x zones).
Multiple named tables share the same zone system.

File layout::

    +---------------------------------------------+
    |  Header records (variable-length, ASCII)     |
    |    PAR record  -> zone count, parameters     |
    |    MVR record  -> table names + precision     |
    |    ROW record  -> sentinel ending the header  |
    +---------------------------------------------+
    |  Data blocks (one per row per table)          |
    |    5-byte envelope: row(u16) tbl(u8) len(u16) |
    |    payload: type byte + compressed data       |
    +---------------------------------------------+

Block Types
-----------

Each data block carries one row of one table.  The **type byte**
(3rd byte of the payload) selects the encoding:

``0x00`` -- **Zero row**
    No data; row is all zeros.  (Most common for sparse transit skims.)

``0x40`` -- **Sparse hi-byte-only**
    Values are multiples of 256.  One sparse section encodes the hi byte;
    the effective value is ``hi * 256``.  Used when all non-zero values in
    a row happen to be exact multiples of 256 (e.g. long drive-to-transit
    distances).

``0x80`` -- **Sparse lo-byte-only**
    Values fit in 0-255.  One sparse section encodes the lo byte directly.

``0xC0`` -- **Sparse 2-byte (lo + hi)**
    Integer values up to 65535.  Two sparse sections: lo bytes then hi bytes.
    Value = ``hi * 256 + lo``.

``0xC8`` -- **Dense/sparse 2-byte + precision**
    Floating-point values.  The ``zone_field`` (u16 at offset 3) selects:

    - **Sparse mode** (``zone_field & 0x8000``): three sparse sections
      (lo, hi, precision).  Value = ``(hi * 256 + lo) / divisor(prec)``.
    - **Dense mode** (``zone_field < zones``): raw + compressed lo bytes,
      compressed hi bytes, compressed precision bytes.  See
      `Dense Block Layout`_ below.

``0xE8`` -- **Dense/sparse 3-byte + precision (wide)**
    Large floating-point values needing a third (mid) byte.

    - **Sparse mode** (``zone_field & 0x8000``): four sparse sections
      (lo, mid, hi, precision).
      Value = ``(hi * 65536 + mid * 256 + lo) / divisor(prec)``.
    - **Dense mode**: raw + compressed lo, compressed mid, sparse hi,
      sparse precision.

Dense Block Layout
------------------

For 0xC8 dense mode, the payload after the type byte is::

    zone_field (u16)     -> n_raw = zone_field & 0x7FFF (0 means zones)
    lo_raw[n_raw]        -> raw lo bytes for zones 0 .. n_raw-1
    lo_cont[zones-n_raw] -> compressed lo bytes for remaining zones
    hi[zones]            -> compressed hi bytes for all zones
    prec[zones]          -> compressed precision bytes for all zones

When ``n_raw == zones``, the lo-continuation section is absent.  When
``n_raw < zones``, the continuation section uses the block codec
(RLE + literal) to encode the remaining lo bytes.  This "short-lo"
pattern appears in highway midday skims where the first *n_raw* zones
have raw data and the rest are compressed.

0xE8 dense mode is identical except a compressed **mid** section sits
between lo and hi, and the hi/prec sections use the sparse codec.

Compression Codecs
------------------

TPP uses two byte-stream compression codecs:

**Block codec** (used for dense lo, hi, mid, prec sections):
    Each instruction is 2 or 3 bytes: ``count_byte``, ``mode_byte``,
    and optionally a fill byte.

    - ``mode & 0x80``: **RLE** -- repeat the next byte
      ``count | ((mode & 0x7F) << 8)`` times.  This allows runs up to
      32767 (not just 255).
    - ``mode == 0x00``: **Literal** -- copy *count* raw bytes.
    - Precision sections also support **shorthand RLE** where
      ``count < 0x80``: the mode byte itself is the fill value,
      repeated *count* times.
    - Otherwise: **varint literal** --
      ``big_count = (count | mode << 8) & 0x7FFF`` raw bytes follow.

**Sparse codec** (used for sparse lo, hi, mid, prec sections):
    Similar 2-byte header with ``count_byte`` and ``mode_byte``:

    - ``mode == 0x00``: literal -- *count* raw bytes follow.
    - ``mode & 0x80``: RLE -- ``(count | mode << 8) & 0x7FFF`` repeats
      of the next byte.
    - Otherwise: varint literal -- ``(count | mode << 8) & 0x7FFF``
      raw bytes.

Precision Encoding
------------------

The precision byte's upper nibble selects a decimal divisor::

    0x00 -> /1          0x10 -> /10         0x20 -> /100 (default)
    0x30 -> /1000       0x40 -> /10000      ...

The stored integer ``(hi * 256 + lo)`` is divided by this to recover
the floating-point value.  Most skim tables use ``0x20`` (/100),
giving centimal precision (e.g. time in minutes, distance in miles).

Implementation Notes
--------------------

- The file is bulk-read into memory; blocks are parsed via buffer offsets
  with no per-block I/O.
- Value assembly uses numpy vectorisation: lo/hi/prec arrays are decoded
  into uint8/uint16 arrays, then combined in bulk ``float64`` arithmetic.
- Pre-built fill tables (``_FILL``) and a precision lookup table
  (``_DIVISOR_LUT``) avoid per-element branching.
"""
import struct
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Precision encoding
# ---------------------------------------------------------------------------
# Upper nibble of the precision byte encodes decimal places:
#   0x00 → ÷1, 0x10 → ÷10, 0x20 → ÷100, …
_PRECISION_DIVISOR = {
    0x00: 1,
    0x10: 10,
    0x20: 100,
    0x30: 1_000,
    0x40: 10_000,
    0x50: 100_000,
    0x60: 1_000_000,
    0x70: 10_000_000,
    0x80: 100_000_000,
    0x90: 1_000_000_000,
}

# Vectorised lookup: precision byte → float divisor  (256 entries)
_DIVISOR_LUT = np.ones(256, dtype=np.float64) * 100.0  # default ÷100
for _k, _v in _PRECISION_DIVISOR.items():
    _DIVISOR_LUT[_k] = float(_v)


# ---------------------------------------------------------------------------
# Block decoders (low-level)
# ---------------------------------------------------------------------------

# Pre-built fill patterns for RLE: _FILL[v] = 32768 bytes of value v
# Slicing a pre-built bytes is faster than bytes([v]) * n each time.
_FILL = [bytes([v]) * 32768 for v in range(256)]


def _decode_blocks(
    raw: bytes,
    max_values: int,
    allow_shorthand: bool = False,
) -> tuple[np.ndarray, int]:
    """Decode a compressed byte stream using the **block codec**.

    Used for the lo-continuation, hi, mid, and precision byte lanes in
    dense (0xC8 / 0xE8) blocks.

    Each instruction is a 2-byte header (count, mode) optionally followed
    by data bytes:

    * ``mode & 0x80`` -- **RLE**: one fill byte follows, repeated
      ``count | ((mode & 0x7F) << 8)`` times.  The 7 upper bits of mode
      extend the count beyond 255, allowing runs up to 32767.
    * ``mode == 0x00`` -- **Literal**: copy the next *count* raw bytes
      verbatim.
    * ``allow_shorthand and count < 0x80`` -- **Shorthand RLE**: *mode*
      itself is the fill value, repeated *count* times.  (Used only for
      the precision lane, where the fill value is a precision code like
      ``0x20``.)
    * Otherwise -- **Varint literal**: ``big_count = (count | mode<<8) & 0x7FFF``
      raw bytes follow.  Handles large literal spans exceeding 255 bytes.

    Parameters
    ----------
    raw : bytes
        The compressed byte stream.
    max_values : int
        Maximum number of output bytes to decode (typically *zones* or
        *zones - n_raw*).
    allow_shorthand : bool
        Enable shorthand RLE (precision lane only).

    Returns
    -------
    tuple[np.ndarray, int]
        ``(uint8_array, bytes_consumed)``.
    """
    out = bytearray(max_values)
    pos = 0
    filled = 0
    raw_len = len(raw)
    remaining = max_values
    _fill = _FILL  # local ref

    while pos + 1 < raw_len and remaining > 0:
        count = raw[pos]
        mode = raw[pos + 1]

        if mode & 0x80:
            if pos + 2 >= raw_len:
                break
            big_count = count | ((mode & 0x7F) << 8)
            n = big_count if big_count <= remaining else remaining
            out[filled : filled + n] = _fill[raw[pos + 2]][:n]
            filled += n
            remaining -= n
            pos += 3

        elif mode == 0x00:
            n = count if count <= remaining else remaining
            out[filled : filled + n] = raw[pos + 2 : pos + 2 + n]
            filled += n
            remaining -= n
            pos += 2 + count

        elif allow_shorthand and count < 0x80:
            n = count if count <= remaining else remaining
            out[filled : filled + n] = _fill[mode][:n]
            filled += n
            remaining -= n
            pos += 2

        else:
            big_count = (count | (mode << 8)) & 0x7FFF
            n = big_count if big_count <= remaining else remaining
            out[filled : filled + n] = raw[pos + 2 : pos + 2 + n]
            filled += n
            remaining -= n
            pos += 2 + big_count

    return np.frombuffer(out, dtype=np.uint8, count=filled), pos


def _decode_sparse(raw: bytes, zones: int) -> tuple[np.ndarray, int]:
    """Decode one sparse section using the **sparse codec**.

    Used for byte lanes in sparse blocks (0x40, 0x80, 0xC0, 0xC8-sparse,
    0xE8-sparse) and for the hi/prec lanes in 0xE8 dense blocks.

    Each instruction is a 2-byte header (count_byte, mode) followed by
    data bytes:

    * ``mode == 0x00`` -- **Literal**: copy the next *count_byte* raw bytes.
    * ``mode & 0x80`` -- **RLE**: count = ``(count_byte | mode<<8) & 0x7FFF``,
      repeat the next byte *count* times.
    * Otherwise -- **Varint literal**: count =
      ``(count_byte | mode<<8) & 0x7FFF``, copy that many raw bytes.

    The sparse codec always emits exactly *zones* output bytes (one per
    column), with implicit zeros for any trailing columns not covered.

    Parameters
    ----------
    raw : bytes
        The compressed byte stream for this section.
    zones : int
        Number of output values (columns) to decode.

    Returns
    -------
    tuple[np.ndarray, int]
        ``(uint16_array, bytes_consumed)`` -- decoded values (promoted to
        uint16 for safe arithmetic) and number of input bytes consumed.
    """
    out = bytearray(zones)
    col = 0
    pos = 0
    raw_len = len(raw)
    _fill = _FILL  # local ref

    while pos + 1 < raw_len and col < zones:
        count_byte = raw[pos]
        mode = raw[pos + 1]
        pos += 2

        if mode == 0x00:
            count = count_byte
            end = col + count
            if end > zones:
                end = zones
            n = end - col
            if pos + n > raw_len:
                break
            out[col:end] = raw[pos : pos + n]
            pos += count
            col = end
        elif mode & 0x80:
            count = (count_byte | (mode << 8)) & 0x7FFF
            if pos >= raw_len:
                break
            end = col + count
            if end > zones:
                end = zones
            out[col:end] = _fill[raw[pos]][:end - col]
            pos += 1
            col = end
        else:
            big_count = (count_byte | (mode << 8)) & 0x7FFF
            end = col + big_count
            if end > zones:
                end = zones
            n = end - col
            if pos + n > raw_len:
                break
            out[col:end] = raw[pos : pos + n]
            pos += big_count
            col = end

    return np.frombuffer(out, dtype=np.uint8).astype(np.uint16), pos


# ---------------------------------------------------------------------------
# Row decoders (vectorised value assembly)
# ---------------------------------------------------------------------------

def _assemble_dense_row(
    lo_bytes: bytes | memoryview,
    hi_values: np.ndarray,
    prec_values: np.ndarray,
    zones: int,
) -> np.ndarray:
    """Combine lo, hi, and precision into a float64 row (vectorised).

    Used for 0xC8 dense blocks.  Value = ``(hi * 256 + lo) / divisor(prec)``.
    """
    lo = np.frombuffer(lo_bytes, dtype=np.uint8).astype(np.float64)

    hi = np.zeros(zones, dtype=np.float64)
    n_hi = min(len(hi_values), zones)
    hi[:n_hi] = hi_values[:n_hi]

    prec = np.full(zones, 0x20, dtype=np.uint8)
    n_pr = min(len(prec_values), zones)
    prec[:n_pr] = prec_values[:n_pr]

    stored = hi * 256.0 + lo
    divisors = _DIVISOR_LUT[prec]
    return stored / divisors


def _assemble_wide_dense_row(
        lo_bytes: bytes | memoryview,
        mid_values: np.ndarray,
        hi_arr: np.ndarray,
        prec_arr: np.ndarray,
        zones: int,
) -> np.ndarray:
        """Combine lo, mid, hi, and precision for 3-byte dense rows.

        Used for 0xE8 dense blocks.
        Value = ``(hi * 65536 + mid * 256 + lo) / divisor(prec)``.

        The byte lanes use a mixed layout:
            - lo byte lane is raw
            - mid byte lane uses the dense block codec
            - hi and precision byte lanes use the sparse codec
        """
        lo = np.frombuffer(lo_bytes, dtype=np.uint8).astype(np.uint32)

        mid = np.zeros(zones, dtype=np.uint32)
        n_mid = min(len(mid_values), zones)
        mid[:n_mid] = mid_values[:n_mid]

        hi = np.zeros(zones, dtype=np.uint32)
        n_hi = min(len(hi_arr), zones)
        hi[:n_hi] = hi_arr[:n_hi]

        prec = np.full(zones, 0x20, dtype=np.uint8)
        n_pr = min(len(prec_arr), zones)
        prec[:n_pr] = prec_arr[:n_pr]

        stored = hi * 65536 + mid * 256 + lo
        divisors = _DIVISOR_LUT[prec]
        return stored.astype(np.float64) / divisors


def _assemble_sparse_row(
    lo_arr: np.ndarray,
    hi_arr: np.ndarray,
) -> np.ndarray:
    """Combine sparse lo/hi into a float64 row (no precision divisor).

    Used for 0xC0 blocks. Value = ``hi * 256 + lo``.
    """
    return hi_arr.astype(np.float64) * 256.0 + lo_arr.astype(np.float64)


# ---------------------------------------------------------------------------
# Header parser
# ---------------------------------------------------------------------------

def _parse_header(fh) -> tuple[int, list[str], list[int]]:
    """Parse TPP header records.

    The header is a sequence of length-prefixed ASCII records:

    - **PAR** record: ``PAR Zones=N ...`` -- zone count and other parameters.
    - **MVR** record: NUL-separated table names, each optionally followed by
      ``=N`` specifying decimal places (default 2 = divisor 100).
    - **ROW** record: sentinel marking the start of data blocks.

    Returns ``(zones, table_names, mspecs)`` where *mspecs* is the
    per-table precision spec list (currently unused but preserved for
    future reference).
    """
    zones = 0
    table_names: list[str] = []
    mspecs: list[int] = []

    while True:
        hdr = fh.read(4)
        if len(hdr) < 4:
            raise ValueError("Unexpected end of file in header")
        rec_len = struct.unpack("<I", hdr)[0]
        if rec_len < 4:
            raise ValueError(f"Invalid header record length: {rec_len}")
        payload = fh.read(rec_len - 4)
        text = payload.rstrip(b"\x00").decode("ascii", errors="replace")

        if text.startswith("PAR "):
            for part in text.split():
                if part.startswith("Zones="):
                    zones = int(part.split("=", 1)[1])
        elif payload[:3] == b"MVR":
            parts = payload.split(b"\x00")
            for p in parts[1:]:
                if p:
                    name = p.decode("ascii", errors="replace")
                    if "=" in name:
                        name, spec = name.split("=", 1)
                        mspecs.append(int(spec))
                    else:
                        mspecs.append(2)  # default precision
                    table_names.append(name)
        elif text == "ROW":
            break

    if zones == 0:
        raise ValueError("Zones count not found in header")
    if not table_names:
        raise ValueError("No table names found in header")

    return zones, table_names, mspecs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_tpp(path: str | Path) -> dict:
    """Read a Cube Voyager TPP matrix file.

    Parses the header to discover zone count and table names, then
    iterates over data blocks.  Each block is a 5-byte envelope
    (row, table index, payload length) followed by a type-byte-tagged
    payload decoded according to the block type (see module docstring
    for the full format specification).

    Parameters
    ----------
    path : str or Path
        Path to the ``.tpp`` file.

    Returns
    -------
    dict
        ``zones``  -- int, number of zones.
        ``tables`` -- list[str], table names in file order.
        ``data``   -- dict mapping table name to ``float64`` array of
        shape ``(zones, zones)``.
    """
    path = Path(path)

    with open(path, "rb") as fh:
        zones, table_names, _mspecs = _parse_header(fh)
        n_tables = len(table_names)

        # Bulk-read remaining data into a buffer for fast offset access
        buf = fh.read()

        # Pre-allocate
        matrices = {
            name: np.zeros((zones, zones), dtype=np.float64)
            for name in table_names
        }

        # Parse data blocks from buffer
        pos = 0
        buf_len = len(buf)

        while pos + 5 <= buf_len:
            row = struct.unpack_from("<H", buf, pos)[0]
            tbl_idx = buf[pos + 2]
            blen = struct.unpack_from("<H", buf, pos + 3)[0]
            plen = max(0, blen - 2)
            pos += 5

            if row < 1 or row > zones or tbl_idx < 1 or tbl_idx > n_tables:
                pos += plen
                continue

            if pos + plen > buf_len or plen < 3:
                pos += plen
                continue

            block_data = buf[pos : pos + plen]
            pos += plen

            tbl_name = table_names[tbl_idx - 1]
            row_idx = row - 1
            type_byte = block_data[2]

            if type_byte == 0x00:
                # All-zero row — already initialised to zero
                pass

            elif type_byte == 0x40:
                # Sparse 1-byte: hi only, values are multiples of 256
                body = block_data[3:]
                hi_arr, _ = _decode_sparse(body, zones)
                matrices[tbl_name][row_idx] = hi_arr.astype(np.float64) * 256.0

            elif type_byte == 0x80:
                # Sparse 1-byte: lo only, values 0–255
                body = block_data[3:]
                lo_arr, _ = _decode_sparse(body, zones)
                matrices[tbl_name][row_idx] = lo_arr.astype(np.float64)

            elif type_byte == 0xC0:
                # Sparse 2-byte: lo + hi sections, integer values
                body = block_data[3:]
                lo_arr, lo_consumed = _decode_sparse(body, zones)
                hi_arr, _ = _decode_sparse(body[lo_consumed:], zones)
                matrices[tbl_name][row_idx] = _assemble_sparse_row(
                    lo_arr, hi_arr
                )

            elif type_byte == 0xC8:
                zone_field = struct.unpack_from("<H", block_data, 3)[0]
                if zone_field & 0x8000:
                    # Sparse mode: lo + hi + prec sections
                    body = block_data[3:]
                    lo_arr, lo_c = _decode_sparse(body, zones)
                    hi_arr, hi_c = _decode_sparse(body[lo_c:], zones)
                    prec_arr, _ = _decode_sparse(body[lo_c + hi_c:], zones)
                    stored = (hi_arr.astype(np.float64) * 256.0
                              + lo_arr.astype(np.float64))
                    divisors = _DIVISOR_LUT[
                        prec_arr.astype(np.uint8)
                    ]
                    matrices[tbl_name][row_idx] = stored / divisors
                else:
                    # Dense mode.  Layout:
                    #   n_raw raw lo bytes  (zones 0 .. n_raw-1)
                    #   compressed lo cont  (zones n_raw .. zones-1)
                    #   compressed hi       (all zones)
                    #   compressed prec     (all zones)
                    n_raw = zone_field & 0x7FFF
                    if n_raw == 0:
                        n_raw = zones

                    # --- lo section ---
                    lo_bytes = block_data[5 : 5 + n_raw]
                    rest = block_data[5 + n_raw :]
                    n_cont = zones - n_raw
                    if n_cont > 0:
                        lo_cont, lo_c = _decode_blocks(
                            rest, max_values=n_cont, allow_shorthand=False
                        )
                        rest = rest[lo_c:]
                    else:
                        lo_cont = np.empty(0, dtype=np.uint8)

                    # --- hi section (all zones) ---
                    hi_arr, hi_c = _decode_blocks(
                        rest, max_values=zones, allow_shorthand=False
                    )
                    rest = rest[hi_c:]

                    # --- prec section (all zones) ---
                    prec_arr, _ = _decode_blocks(
                        rest, max_values=zones, allow_shorthand=True
                    )

                    # Assemble: hi * 256 + lo, then divide by precision
                    dest = matrices[tbl_name][row_idx]
                    n_hi = len(hi_arr)
                    dest[:n_hi] = hi_arr[:n_hi].astype(np.float64) * 256.0

                    lo_raw = np.frombuffer(lo_bytes, dtype=np.uint8)
                    dest[: len(lo_raw)] += lo_raw
                    if len(lo_cont) > 0:
                        dest[n_raw : n_raw + len(lo_cont)] += lo_cont

                    n_pr = len(prec_arr)
                    n_eff = min(n_hi, n_pr, zones)
                    np.divide(
                        dest[:n_eff],
                        _DIVISOR_LUT[prec_arr[:n_eff]],
                        out=dest[:n_eff],
                    )

            elif type_byte == 0xE8:
                zone_field = struct.unpack_from("<H", block_data, 3)[0]
                if zone_field & 0x8000:
                    # Sparse mode: lo + mid + hi + prec sections
                    body = block_data[3:]
                    lo_arr, lo_c = _decode_sparse(body, zones)
                    mid_arr, mid_c = _decode_sparse(body[lo_c:], zones)
                    hi_arr, hi_c = _decode_sparse(
                        body[lo_c + mid_c:], zones
                    )
                    prec_arr, _ = _decode_sparse(
                        body[lo_c + mid_c + hi_c:], zones
                    )
                    stored = (
                        hi_arr.astype(np.uint32) * 65536
                        + mid_arr.astype(np.uint32) * 256
                        + lo_arr.astype(np.uint32)
                    )
                    divisors = _DIVISOR_LUT[
                        prec_arr.astype(np.uint8)
                    ]
                    matrices[tbl_name][row_idx] = (
                        stored.astype(np.float64) / divisors
                    )
                else:
                    # Dense mode.  Layout (same continuation pattern as 0xC8):
                    #   n_raw raw lo bytes  (zones 0 .. n_raw-1)
                    #   compressed lo cont  (zones n_raw .. zones-1)
                    #   compressed mid      (all zones)
                    #   sparse hi           (all zones)
                    #   sparse prec         (all zones)
                    n_raw = zone_field & 0x7FFF
                    if n_raw == 0:
                        n_raw = zones

                    # --- lo section ---
                    lo_bytes = block_data[5 : 5 + n_raw]
                    rest = block_data[5 + n_raw :]
                    n_cont = zones - n_raw
                    if n_cont > 0:
                        lo_cont, lo_c = _decode_blocks(
                            rest, max_values=n_cont, allow_shorthand=False
                        )
                        rest = rest[lo_c:]
                        # Build full lo array
                        full_lo = np.zeros(zones, dtype=np.uint8)
                        raw_lo = np.frombuffer(lo_bytes, dtype=np.uint8)
                        full_lo[: len(raw_lo)] = raw_lo
                        full_lo[n_raw : n_raw + len(lo_cont)] = lo_cont
                        lo_bytes = bytes(full_lo)
                    # else: lo_bytes already covers all zones

                    # --- mid section (all zones) ---
                    mid_values, mid_consumed = _decode_blocks(
                        rest, max_values=zones, allow_shorthand=False
                    )
                    sparse_tail = rest[mid_consumed:]

                    # --- hi / prec sections (sparse, all zones) ---
                    hi_arr, hi_consumed = _decode_sparse(
                        sparse_tail, zones
                    )
                    prec_arr, _ = _decode_sparse(
                        sparse_tail[hi_consumed:], zones
                    )
                    matrices[tbl_name][row_idx] = _assemble_wide_dense_row(
                        lo_bytes, mid_values, hi_arr, prec_arr, zones
                    )

            else:
                raise ValueError(
                    f"Unknown block type 0x{type_byte:02X} at "
                    f"row={row}, table={tbl_name}"
                )

    return {
        "zones": zones,
        "tables": table_names,
        "data": matrices,
    }
