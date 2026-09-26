# Transit line link inventory

This standalone diagnostic utility expands every route in a CUBE `.lin` file
into its directed node-to-node links and saves the result as Parquet.

Each output row contains:

| Column | Meaning |
| --- | --- |
| `A` | Link start node |
| `B` | Link end node |
| `NAME` | Transit line name |
| `MODE` | Transit line mode |
| `OPERATOR` | `OWNER` in a TRNBUILD file or `OPERATOR` in a PT file |
| `DIRECTION` | `0` for the coded direction; `1` for the generated reverse direction |

Negative node signs identify non-stops in a line file. The utility intentionally
removes the sign because stop status does not affect highway-link existence.
For `ONEWAY=FALSE`, it writes both the coded sequence and its reverse. A missing
`ONEWAY` is treated as true.

## Run with uv

From this directory:

```bash
uv sync
uv run python transit_line_links.py /path/to/transitLines.lin /path/to/output
```

Or from the repository root after installing `pandas` and `pyarrow`:

```bash
python utilities/pt_converter/utilities/transit_line_links/transit_line_links.py \
  /path/to/transitLines.lin \
  /path/to/output
```

The default output is:

```text
/path/to/output/transit_route_links.parquet
```

Use `--output-name another_name.parquet` to change the filename.

## Test

The parser and route expansion tests use only the Python standard library:

```bash
python -m unittest discover -s tests -v
```
