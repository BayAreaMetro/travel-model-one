USAGE = """

python aggregateTransitLinks.py AM|MD|PM|EV|EA

 Aggregates the per-submode Cube transit assignment CSV/DBF files into a single
 trnlink[timeperiod].dbf without a NetworkWrangler dependency.

 Dependencies: pandas, dbfpy3, simpledbf
 Note: simpledbf needs to be used for reading (rather than dbfpy3, which is
 used for writing) because dbfpy3 validation is too strict for Cube's output files.

 Reads from the current directory:
   trnlink{tp}_{mode}.csv   for each mode in $ALLTRIPMODES
   trnlink{tp}_{mode}.dbf   first mode only (provides FREQ and SEQ, absent from CSV)

 Reads from the parent directory (..):
   transitLineToVehicle.csv
   transitVehicleToCapacity.csv
   transitPrefixToVehicle.csv

 Writes to the current directory:
   trnlink{timeperiod}.dbf

"""
import csv, logging, os, sys

import dbfpy3.dbf
from simpledbf import Dbf5
import pandas as pd

# ---------------------------------------------------------------------------
# TM1 constants
# (previously sourced from Wrangler.TransitLine and Wrangler.Network)
# ---------------------------------------------------------------------------

# https://github.com/BayAreaMetro/modeling-website/wiki/TimePeriods
HOURS_PER_TIMEPERIOD = {"EA": 3.0, "AM": 4.0, "MD": 5.0, "PM": 4.0, "EV": 8.0}

# Index into line_to_attrs list for vehicle type, keyed by time period
TIMEPERIOD_TO_VEHTYPIDX = {"AM": 2, "MD": 4, "PM": 3, "EV": 4, "EA": 4}

# Link modes to exclude: walk/drive access connectors, egress, and funnel links
IGNORE_MODES = {1, 2, 3, 4, 5, 6, 7}

# Transit line modes that use the Muni peak-hour peaking factor override
MUNI_MODES = {20, 21, 110}  # cable car, local bus, LRT

ADDITIVE_FIELDS = [
    "AB_VOL", "AB_BRDA", "AB_XITA", "AB_BRDB", "AB_XITB",
    "BA_VOL", "BA_BRDA", "BA_XITA", "BA_BRDB", "BA_XITB",
]

# Column names for the headerless Cube transit assignment CSV output.
# Cube may append an extra Cube-internal code as a 21st column; it is ignored.
CSV_COLNAMES = [
    "A", "B", "TIME", "MODE",
    "PLOT", "STOP_A", "STOP_B", "DIST",
    "NAME", "OWNER",
    "AB_VOL", "AB_BRDA", "AB_XITA", "AB_BRDB", "AB_XITB",
    "BA_VOL", "BA_BRDA", "BA_XITA", "BA_BRDB", "BA_XITB",
]

# DBF output field definitions: [type, name, width] or [type, name, width, decimals]
# Matches the schema written by Wrangler TransitAssignmentData.writeDbfs()
DBF_FIELDS = [
    ["N", "A",          7    ],
    ["N", "B",          7    ],
    ["N", "TIME",       5    ],
    ["N", "MODE",       3    ],
    ["N", "FREQ",       6,  2],
    ["N", "PLOT",       1    ],
    ["N", "COLOR",      2    ],
    ["N", "STOP_A",     1    ],
    ["N", "STOP_B",     1    ],
    ["N", "DIST",       4    ],
    ["C", "NAME",      13    ],
    ["N", "SEQ",        3    ],
    ["C", "OWNER",     10    ],
    ["C", "AB",        15    ],
    ["C", "ABNAMESEQ", 30    ],
    ["C", "FULLNAME",  40    ],
    ["C", "SYSTEM",    25    ],
    ["C", "GROUP",     20    ],
    ["C", "VEHTYPE",   40    ],
    ["N", "VEHCAP",     8,  2],
    ["N", "PERIODCAP", 15,  2],
    ["N", "LOAD",       7,  3],
    ["N", "AB_VOL",     9,  2],
    ["N", "AB_BRDA",    9,  2],
    ["N", "AB_XITA",    9,  2],
    ["N", "AB_BRDB",    9,  2],
    ["N", "AB_XITB",    9,  2],
    ["N", "BA_VOL",     9,  2],
    ["N", "BA_BRDA",    9,  2],
    ["N", "BA_XITA",    9,  2],
    ["N", "BA_BRDB",    9,  2],
    ["N", "BA_XITB",    9,  2],
]

# ---------------------------------------------------------------------------
# Capacity file readers
# (previously Wrangler.TransitCapacity)
# ---------------------------------------------------------------------------

def read_capacity_files(capacity_dir):
    """
    Read the three transit capacity CSV files from capacity_dir.

    Returns:
      line_to_attrs:     linename (upper) -> [system, fullname, AM_vtype, PM_vtype, OP_vtype]
      veh_to_capacity:   vehtype -> float seat capacity
      prefix_to_vehicle: prefix (upper, 3-4 chars) -> [system, vehtype]
    """
    line_to_attrs = {}
    l2v_path = os.path.join(capacity_dir, "transitLineToVehicle.csv")
    with open(l2v_path, newline="") as f:
        for name, system, _stripped, _simple, fullname, vt_am, vt_pm, vt_op in csv.reader(f):
            line_to_attrs[name.upper()] = [system, fullname, vt_am, vt_pm, vt_op]
    logging.info(f"Read {len(line_to_attrs)} entries from {l2v_path}")

    veh_to_capacity = {}
    v2c_path = os.path.join(capacity_dir, "transitVehicleToCapacity.csv")
    with open(v2c_path, newline="") as f:
        for tokens in csv.reader(f):
            if tokens[0] == "VehicleType":
                continue
            veh_to_capacity[tokens[0]] = float(tokens[1])
    logging.info(f"Read {len(veh_to_capacity)} entries from {v2c_path}")

    prefix_to_vehicle = {}
    p2v_path = os.path.join(capacity_dir, "transitPrefixToVehicle.csv")
    with open(p2v_path, newline="") as f:
        for prefix, system, vehtype in csv.reader(f):
            prefix_to_vehicle[prefix.upper()] = [system, vehtype]
    logging.info(f"Read {len(prefix_to_vehicle)} entries from {p2v_path}")

    return line_to_attrs, veh_to_capacity, prefix_to_vehicle


def get_system_and_vehicletype(linename, timeperiod, line_to_attrs, prefix_to_vehicle):
    """Return (system, vehicletype) for a line name, falling back to prefix lookup."""
    key = linename.upper()
    if key in line_to_attrs:
        idx = TIMEPERIOD_TO_VEHTYPIDX[timeperiod]
        return line_to_attrs[key][0], line_to_attrs[key][idx]
    for prefix_len in [4, 3]:
        prefix = key[:prefix_len]
        if prefix in prefix_to_vehicle:
            return prefix_to_vehicle[prefix][0], prefix_to_vehicle[prefix][1]
    return "", ""


# ---------------------------------------------------------------------------
# Core aggregation
# (previously Wrangler.TransitAssignmentData.__init__ + readTransitAssignmentCsvs)
# ---------------------------------------------------------------------------

def aggregate_transit_links(timeperiod, modes, capacity_dir):
    """
    Read per-submode Cube CSV/DBF files and return a single aggregated DataFrame.

    For the first mode, all non-additive fields are populated. TIME and DIST from
    the CSV are multiplied by 100 (stored as integer hundredths, matching the legacy
    DBF format expected by downstream consumers such as Quickboards).
    FREQ and SEQ come from the first mode's DBF output, which Cube writes alongside
    the CSV but with those two columns filled in.
    For all subsequent modes, only the ADDITIVE_FIELDS are summed in.
    """
    tp = timeperiod
    tp_lower = tp.lower()
    hours = HOURS_PER_TIMEPERIOD[tp]

    # tpfactor = "constant_with_peaked_muni"
    # Default: 1 / hours_in_period (converts period volume to peak-hour volume)
    default_tpf = 1.0 / hours
    # Muni lines use an empirical peaking factor instead
    muni_tpf = {"AM": 0.45, "MD": 1.0 / HOURS_PER_TIMEPERIOD["MD"],
                "PM": 0.45, "EV": 0.2,  "EA": 1.0 / HOURS_PER_TIMEPERIOD["EA"]}[tp]

    line_to_attrs, veh_to_capacity, prefix_to_vehicle = read_capacity_files(capacity_dir)

    df = None  # master DataFrame, built from the first mode

    for mode_idx, mode in enumerate(modes):
        csv_path = f"trnlink{tp_lower}_{mode}.csv"
        logging.info(f"Reading {csv_path}")

        # Cube emits headerless CSVs; supply names explicitly and drop the extra
        # Cube-internal code column if present (21st field, e.g. "TPPL0019").
        mode_df = pd.read_csv(
            csv_path, dtype=str,
            header=None, names=CSV_COLNAMES,
            usecols=range(len(CSV_COLNAMES)),
        )
        # Drop header row if Cube happened to emit one (first A-column value == "A")
        if mode_df.iloc[0]["A"].strip().upper() == "A":
            mode_df = mode_df.iloc[1:].reset_index(drop=True)

        # Preserve original 0-based row index before filtering so we can look up
        # the matching row in the DBF (which includes every row, filtered or not)
        mode_df.insert(0, "_orig_idx", range(len(mode_df)))

        # Drop walk/drive access, egress, and funnel link rows
        mode_df = mode_df[~mode_df["MODE"].astype(int).isin(IGNORE_MODES)].reset_index(drop=True)
        logging.info(f"  Retained {len(mode_df)} records (of which {mode_idx == 0 and 'building master table' or 'summing volumes'})")

        if mode_idx == 0:
            # ------------------------------------------------------------------
            # First mode: build the master DataFrame with all non-additive fields
            # ------------------------------------------------------------------
            keep = ["_orig_idx", "A", "B", "TIME", "MODE", "PLOT",
                    "STOP_A", "STOP_B", "DIST", "NAME", "OWNER"] + ADDITIVE_FIELDS
            df = mode_df[keep].copy()

            # FREQ and SEQ are absent from the CSV; read them from the parallel DBF
            dbf_path = f"trnlink{tp_lower}_{mode}.dbf"
            logging.info(f"Reading {dbf_path} for FREQ and SEQ")
            dbf_df = Dbf5(dbf_path).to_dataframe()[["FREQ", "SEQ"]]
            # Map by original row index (DBF rows correspond 1-to-1 with CSV rows)
            df["FREQ"] = df["_orig_idx"].map(dbf_df["FREQ"])
            df["SEQ"]  = df["_orig_idx"].map(dbf_df["SEQ"])

            # Integer columns
            for col in ["A", "B", "MODE", "PLOT", "STOP_A", "STOP_B"]:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
            df["SEQ"]  = df["SEQ"].fillna(0).astype(int)
            # Float columns
            df["FREQ"] = pd.to_numeric(df["FREQ"], errors="coerce").fillna(0.0)
            for col in ADDITIVE_FIELDS:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            # TIME (minutes) and DIST (miles) are stored as integer hundredths in the DBF
            df["TIME"] = (pd.to_numeric(df["TIME"], errors="coerce").fillna(0.0) * 100).astype(int)
            df["DIST"] = (pd.to_numeric(df["DIST"], errors="coerce").fillna(0.0) * 100).astype(int)
            # String columns
            df["NAME"]  = df["NAME"].str.strip().fillna("")
            df["OWNER"] = df["OWNER"].str.strip().fillna("")

            # Fields absent from the CSV and always constant for this call
            df["COLOR"] = 0   # not present in TM1 CSV output
            df["GROUP"] = ""  # line grouping not used (grouping=None)

            # AB: "A B" string used as a link identifier
            df["AB"] = df["A"].astype(str) + " " + df["B"].astype(str)

            # ABNAMESEQ: unique key per link-line-sequence record.
            # Format is "A B NAME [SEQ]" where SEQ is only appended when non-zero.
            # Duplicates (rare) are resolved by incrementing SEQ.
            abnameseq_list = []
            seen_keys = set()
            for _, row in df.iterrows():
                base = f"{row['A']} {row['B']} {row['NAME']}"
                seq = int(row["SEQ"])
                if seq > 0:
                    candidate = f"{base} {seq}"
                    while candidate in seen_keys:
                        seq += 1
                        candidate = f"{base} {seq}"
                    seen_keys.add(candidate)
                    abnameseq_list.append(candidate)
                else:
                    seen_keys.add(base)
                    abnameseq_list.append(base)
            df["ABNAMESEQ"] = abnameseq_list

            # Capacity lookups: SYSTEM, FULLNAME, VEHTYPE, VEHCAP, PERIODCAP
            warn_lines = set()
            systems, fullnames, vehtypes, vehcaps, periodcaps = [], [], [], [], []
            for _, row in df.iterrows():
                linename = row["NAME"]
                system, vehtype = get_system_and_vehicletype(
                    linename, tp, line_to_attrs, prefix_to_vehicle)
                fullname = line_to_attrs.get(linename.upper(), [None, ""])[1]

                if system == "" and linename not in warn_lines:
                    logging.warning(f"No default system for line: {linename}")
                    warn_lines.add(linename)

                try:
                    if vehtype not in veh_to_capacity:
                        raise KeyError(vehtype)
                    vehcap = veh_to_capacity[vehtype]
                    freq = row["FREQ"]
                    periodcap = (hours * 60.0 * vehcap / freq) if freq > 0 else 0.0
                except KeyError:
                    vehcap, periodcap = 0, 0.0

                systems.append(system)
                fullnames.append(fullname)
                vehtypes.append(vehtype)
                vehcaps.append(float(vehcap))
                periodcaps.append(periodcap)

            df["SYSTEM"]    = systems
            df["FULLNAME"]  = fullnames
            df["VEHTYPE"]   = vehtypes
            df["VEHCAP"]    = vehcaps
            df["PERIODCAP"] = periodcaps

        else:
            # ------------------------------------------------------------------
            # Subsequent modes: sum the additive volume fields into the master df.
            # All mode files have the same link rows in the same order after
            # filtering, so positional (value-array) addition is correct.
            # ------------------------------------------------------------------
            if len(mode_df) != len(df):
                logging.error(
                    f"Mode {mode} yielded {len(mode_df)} rows after filtering "
                    f"but expected {len(df)} — skipping this mode"
                )
                continue
            for col in ADDITIVE_FIELDS:
                df[col] += pd.to_numeric(mode_df[col], errors="coerce").fillna(0.0).values

    # LOAD = AB_VOL * tpfactor * FREQ / (60 * VEHCAP)
    # This gives peak-hour passengers per vehicle (a load factor relative to capacity).
    # Muni line modes use an empirical peaking factor instead of the uniform default.
    def compute_load(row):
        if row["VEHCAP"] == 0 or row["FREQ"] == 0:
            return 0.0
        tpf = muni_tpf if row["MODE"] in MUNI_MODES else default_tpf
        return row["AB_VOL"] * tpf * row["FREQ"] / (60.0 * row["VEHCAP"])

    df["LOAD"] = df.apply(compute_load, axis=1)

    return df


# ---------------------------------------------------------------------------
# DBF writer
# (uses dbfpy3, matching the pattern in model-files/scripts/preprocess/csvToDbf.py)
# ---------------------------------------------------------------------------

def write_dbf(df, out_path):
    """Write the aggregated DataFrame to a DBF file."""
    new_dbf = dbfpy3.dbf.Dbf(out_path, new=True)
    for field_def in DBF_FIELDS:
        new_dbf.add_field(field_def)

    for _, row in df.iterrows():
        rec = new_dbf.new()
        for field_def in DBF_FIELDS:
            ftype, fname, width = field_def[0], field_def[1], field_def[2]
            val = row[fname]
            try:
                if ftype == "C":
                    rec[fname] = str(val)[:width] if pd.notna(val) else ""
                elif len(field_def) == 3:    # integer N (no decimals entry)
                    rec[fname] = int(val)    if pd.notna(val) else 0
                else:                        # float N (has decimals entry)
                    rec[fname] = float(val)  if pd.notna(val) else 0.0
            except (ValueError, TypeError):
                rec[fname] = ("" if ftype == "C" else 0)
        new_dbf.append(rec)

    new_dbf.close()
    logging.info(f"Wrote {len(df)} records to {out_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(USAGE)
        sys.exit(1)

    timeperiod = sys.argv[1].upper()
    if timeperiod not in HOURS_PER_TIMEPERIOD:
        print(f"Invalid timeperiod '{timeperiod}'. Must be one of: {list(HOURS_PER_TIMEPERIOD.keys())}")
        sys.exit(1)

    out_path = f"trnlink{timeperiod}.dbf"

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M",
        handlers=[logging.FileHandler(f"aggregateTransitLinks_{timeperiod}.log", mode="w")],
    )

    if "ALLTRIPMODES" not in os.environ:
        logging.error("ALLTRIPMODES environment variable is not set")
        sys.exit(1)
    modes = os.environ["ALLTRIPMODES"].split()
    logging.info(f"Time period: {timeperiod}   Modes ({len(modes)}): {modes}")

    logging.info(f"Reading transit assignment data for {timeperiod}")
    df = aggregate_transit_links(timeperiod, modes, capacity_dir="..")

    logging.info(f"Writing {out_path}")
    write_dbf(df, out_path)
    print(f"Wrote {len(df)} records to {out_path}")