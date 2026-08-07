# Skim Conversion Mapping: Cube TPP → ActivitySim OMX

Authoritative reference for converting TM1 Cube Voyager TPP skim matrices to
the `skims.omx` that ActivitySim expects.  Maintained alongside
[`scripts/build_omx_skims.py`](../scripts/build_omx_skims.py).

## Conventions

- **OMX key format:** `{ASIM_KEY}__{PERIOD}` (double underscore). ActivitySim
  splits on `__`; keys without it are period-independent.
- **Periods:** `EA`, `AM`, `MD`, `PM`, `EV`
- **Zones:** 1-based TAZ IDs (1 … 1454), stored as OMX mapping `"zone"`.
- **Units are transferred as-is.** Highway: minutes / miles / cents (2000$).
  Transit: stored as ×100 integers — UECs already divide.

---

## 1. Highway Skims

**Source:** `HWYSKM{PERIOD}.tpp` — 21 personal-vehicle tables per file.

| Cube Table | ASIM Key | | Cube Table | ASIM Key |
|---|---|---|---|---|
| `TIMEDA` | `SOV_TIME` | | `TIMES2` | `HOV2_TIME` |
| `DISTDA` | `SOV_DIST` | | `DISTS2` | `HOV2_DIST` |
| `BTOLLDA` | `SOV_BTOLL` | | `BTOLLS2` | `HOV2_BTOLL` |
| `TOLLTIMEDA` | `SOVTOLL_TIME` | | `TOLLTIMES2` | `HOV2TOLL_TIME` |
| `TOLLDISTDA` | `SOVTOLL_DIST` | | `TOLLDISTS2` | `HOV2TOLL_DIST` |
| `TOLLBTOLLDA` | `SOVTOLL_BTOLL` | | `TOLLBTOLLS2` | `HOV2TOLL_BTOLL` |
| `TOLLVTOLLDA` | `SOVTOLL_VTOLL` | | `TOLLVTOLLS2` | `HOV2TOLL_VTOLL` |

| Cube Table | ASIM Key |
|---|---|
| `TIMES3` | `HOV3_TIME` |
| `DISTS3` | `HOV3_DIST` |
| `BTOLLS3` | `HOV3_BTOLL` |
| `TOLLTIMES3` | `HOV3TOLL_TIME` |
| `TOLLDISTS3` | `HOV3TOLL_DIST` |
| `TOLLBTOLLS3` | `HOV3TOLL_BTOLL` |
| `TOLLVTOLLS3` | `HOV3TOLL_VTOLL` |

**21 tables × 5 periods = 105 OMX matrices.**
`COM_HWYSKIM{PERIOD}.tpp` (commercial vehicles) is excluded — truck model only.

---

## 2. Transit Skims

**Source:** `trnskm{period}_{access}_{mode}_{egress}[.avg.iter{N}].tpp` —
27 tables per file.  Prefer highest `.avg.iter{N}` (converged MSA); fall back
to un-averaged.

**Access/egress:** `wlk`/`wlk` → `WLK_*_WLK`, `drv`/`wlk` → `DRV_*_WLK`,
`wlk`/`drv` → `WLK_*_DRV`.

**Modes:** `loc`→`LOC`, `lrf`→`LRF`, `exp`→`EXP`, `hvy`→`HVY`, `com`→`COM`.
`trn` (generic all-transit) is **excluded** — used only for accessibility, not
by mode choice UECs.

### Table Mapping

| Cube Table | ASIM Suffix | Conditions |
|---|---|---|
| `ivt` | `_TOTIVT` | All paths |
| `iwait` | `_IWAIT` | All paths |
| `xwait` | `_XWAIT` | All paths |
| `waux` | `_WAUX` | All paths |
| `fare` | `_FAR` | All paths |
| `boards` | `_BOARDS` | All paths |
| `dtime` | `_DTIM` | Drive paths only |
| `ddist` | `_DDIST` | Drive paths only |
| `ivt{MODE}` | `_KEYIVT` | Mode matching file's line-haul (not LOC — see below) |
| `ivtFerry` | `_FERRYIVT` | LRF paths only |

**OMX key = `{ACCESS}_{MODE}_{EGRESS}{SUFFIX}__{PERIOD}`**
e.g. `WLK_COM_WLK_TOTIVT__AM`, `DRV_HVY_WLK_DDIST__PM`.

### KEYIVT and FERRYIVT

Each TPP file contains IVT breakdowns for *all* sub-modes (feeders are
included).  `KEYIVT` extracts only the file's own line-haul mode:
`ivtCOM` from COM files, `ivtHVY` from HVY, `ivtEXP` from EXP, `ivtLRF` from
LRF.  **LOC has no KEYIVT** — mode choice uses `TOTIVT` directly (local bus is
the only mode).  `FERRYIVT` (`ivtFerry`) is only emitted from LRF files.

### Dropped Tables

`wacc`, `wegr`, `wait`, `ivtMUNILoc`, `ivtMUNIMet`, `distLOC`…`distFerry`,
`firstMode`, `distRegFar` — none referenced by any ActivitySim UEC.

---

## 3. Non-Motorized Skims

**Source:** `nonmotskm.tpp` — **no period suffix** (time-invariant).

| Cube Table | ASIM Key |
|---|---|
| `DISTWALK` | `DISTWALK` |
| `DISTBIKE` | `DISTBIKE` |
| `DIST` | `DIST` |

---

## 4. Summary

| Category | OMX Matrices | Period-indexed? |
|---|---|---|
| Highway | 105 | Yes |
| Transit | ~685 | Yes |
| Non-motorized | 3 | No |
| **Total** | **~793** | |
