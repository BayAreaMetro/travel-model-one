"""Pure-Python writer for Cube Voyager TPP matrix files — inverse of ``read_tpp``.

Emits a *valid* TPP that (a) round-trips through :func:`cubeio.read_tpp` and
(b) Cube Voyager's MATRIX program can read.  It does **not** reproduce Cube's
exact byte choices — it picks the simplest valid encoding per row:

- all-zero rows  -> ``0x00`` block (``80 80 00``)
- otherwise      -> ``0xC8`` dense (2-byte) or ``0xE8`` dense (3-byte) with
  per-cell precision, so mixed-magnitude rows round-trip exactly.

Layout reproduced from the reader (see :mod:`cubeio.tpp_read`):

- Header: length-prefixed ASCII records ``MAT`` / ``ID`` / ``PAR`` / ``MVR`` /
  ``ROW`` (each ``[u32 len incl. self][payload]``).
- Data block: 5-byte envelope ``<H row><B tbl><H blen>`` (1-based; ``blen =
  len(payload) + 2``), then payload ``80 80 <type> ...``.  Blocks are written
  row-major (table fastest), one per (row, table) including zero rows.

Dense block (``zone_field = zones`` -> all lo bytes raw, no continuation):

- ``0xC8``: ``80 80 C8 <H zones> lo[zones] hi prec``  (hi/prec block codec)
- ``0xE8``: ``80 80 E8 <H zones> lo[zones] mid hi prec``  (mid block; hi/prec sparse)

Stored integer per cell = ``round(value * 10**dp)``; the per-cell precision byte
is ``dp << 4`` (reader divides by ``10**dp``).  ``dp`` is the largest value in
``0..MAX_DP`` whose stored integer fits the block's bit width.
"""

import struct
from pathlib import Path

import numpy as np

# Max decimal places to encode. 4 covers skim/trip precision; capping keeps the
# stored integers small. Higher-magnitude cells automatically use fewer places.
_MAX_DP = 4
_C8_MAX = 0xFFFF  # 2-byte stored ceiling
_E8_MAX = 0xFFFFFF  # 3-byte stored ceiling
_RLE_MIN_RUN = 4  # runs >= this encode as RLE (3 bytes) rather than literal


# ---------------------------------------------------------------------------
# Byte-stream encoders (inverse of the reader's _decode_blocks / _decode_sparse)
# ---------------------------------------------------------------------------


def _encode_section(b: bytes) -> bytes:
    """RLE + literal codec, valid for **both** the block and sparse decoders.

    Uses only the two instruction forms Cube itself emits (verified against the
    golden files) — NOT the reader's lenient varint-literal, which crashes Cube:

    - ``[count][0x00][count bytes]``  literal, ``count <= 255``
    - ``[count][0x80][fill]``         RLE, run ``= count <= 255``

    These byte layouts decode identically under ``_decode_blocks`` and
    ``_decode_sparse``.  Runs/literals longer than 255 are split into 255-byte
    chunks (matching Cube, which never exceeds an 8-bit count here).
    """
    out = bytearray()
    n = len(b)
    i = 0
    lit = bytearray()

    def flush() -> None:
        s = 0
        while s < len(lit):
            c = min(len(lit) - s, 255)
            out.append(c)
            out.append(0x00)
            out.extend(lit[s : s + c])
            s += c
        lit.clear()

    while i < n:
        j = i + 1
        while j < n and b[j] == b[i]:
            j += 1
        run = j - i
        if run >= _RLE_MIN_RUN:  # RLE (3 bytes) clearly beats a literal of this run
            flush()
            r = run
            while r > 0:
                c = min(r, 255)
                out.append(c)
                out.append(0x80)
                out.append(b[i])
                r -= c
        else:
            lit += b[i:j]
        i = j
    flush()
    return bytes(out)


# ---------------------------------------------------------------------------
# Per-row encoder
# ---------------------------------------------------------------------------


def _choose_precision(av: np.ndarray, ceiling: int) -> np.ndarray:
    """Per-cell decimal places: largest dp in 0..MAX_DP whose stored int fits."""
    dp = np.zeros(len(av), dtype=np.int16)
    for d in range(_MAX_DP + 1):
        stored = np.rint(av * (10.0**d))
        dp[stored <= ceiling] = d
    return dp


def _encode_row(values: np.ndarray, zones: int) -> bytes:
    """Encode one matrix row to a block payload (``80 80 <type> ...``)."""
    if not values.any():
        return b"\x80\x80\x00"

    av = np.abs(values.astype(np.float64))
    # 0xC8 if every cell fits 2 bytes at dp=0, else 0xE8.
    wide = float(av.max()) > _C8_MAX
    ceiling = _E8_MAX if wide else _C8_MAX

    dp = _choose_precision(av, ceiling)
    stored = np.rint(av * (10.0 ** dp)).astype(np.uint32)
    prec = (dp.astype(np.uint8) << 4)

    lo = (stored & 0xFF).astype(np.uint8).tobytes()
    if wide:
        mid = ((stored >> 8) & 0xFF).astype(np.uint8)
        hi = ((stored >> 16) & 0xFF).astype(np.uint8)
        # 0xE8 dense: lo raw, mid block-codec, hi sparse, prec sparse
        return (
            b"\x80\x80\xe8"
            + struct.pack("<H", zones)
            + lo
            + _encode_section(mid.tobytes())
            + _encode_section(hi.tobytes())
            + _encode_section(prec.tobytes())
        )
    hi = ((stored >> 8) & 0xFF).astype(np.uint8)
    # 0xC8 dense: lo raw, hi block-codec, prec block-codec
    return (
        b"\x80\x80\xc8"
        + struct.pack("<H", zones)
        + lo
        + _encode_section(hi.tobytes())
        + _encode_section(prec.tobytes())
    )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


def _record(payload: bytes) -> bytes:
    """Wrap a header payload as ``[u32 len incl. self][payload]``."""
    return struct.pack("<I", len(payload) + 4) + payload


def _header(zones: int, tables: list[str], dp: int = 2) -> bytes:
    n = len(tables)
    mvr = b"MVR " + str(n).encode() + b"\x00"
    for name in tables:
        mvr += f"{name}={dp}".encode() + b"\x00"
    return b"".join(
        _record(p)
        for p in (
            b"MAT PGM=MATRIX cubeio\x00",
            b"ID=cubeio\x00",
            f"PAR Zones={zones} M={n}".encode() + b"\x00",
            mvr,
            b"ROW\x00",
        )
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_tpp(path: str | Path, data: dict[str, np.ndarray], zones: int | None = None) -> None:
    """Write named square matrices to a Cube TPP file.

    Parameters
    ----------
    path : str or Path
        Output ``.tpp`` path.
    data : dict[str, ndarray]
        ``{table_name: (zones, zones) array}``.  All tables share one zone system.
    zones : int, optional
        Zone count; inferred from the first matrix if omitted.
    """
    tables = list(data)
    if not tables:
        msg = "write_tpp: no tables provided"
        raise ValueError(msg)
    if zones is None:
        zones = data[tables[0]].shape[0]
    for name, m in data.items():
        if m.shape != (zones, zones):
            msg = f"table {name!r} has shape {m.shape}, expected ({zones}, {zones})"
            raise ValueError(msg)

    path = Path(path)
    with path.open("wb") as fh:
        fh.write(_header(zones, tables))
        for row in range(zones):  # 1-based on disk
            for tbl_idx, name in enumerate(tables, start=1):
                payload = _encode_row(np.ascontiguousarray(data[name][row]), zones)
                fh.write(struct.pack("<HBH", row + 1, tbl_idx, len(payload) + 2))
                fh.write(payload)
