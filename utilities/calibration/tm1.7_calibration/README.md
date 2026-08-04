# TM1.7 Calibration Report

A [Quarto book](https://quarto.org/docs/books/) documenting the calibration and
validation of the Travel Model 1.7 (TM1.7). The report will include the updates to
TM1.7 and document the methodology and targets for calibrating and validating the model.

**Important Note: This is separate from the parent folder, FMS-Notebook-Hub and users need to render the report in the correct folder**

## Structure

```
tm1.7_calibration/
├── _quarto.yml          # Quarto book config (chapters, formats, execution)
├── index.qmd            # Book landing page
├── references.bib       # Bibliography
├── environment.yaml     # Conda environment definition
├── .env                 # Local secrets (CENSUS_KEY) — git-ignored, not committed
├── chapter/             # Report chapters (.qmd)
│   ├── 01-intro.qmd
│   ├── 02-calibration.qmd
│   ├── 03-validation.qmd
│   ├── 04-summary.qmd
│   ├── references.qmd
│   ├── _02_uwsl.qmd          # Helper: Usual Work & School Location subsection
│   ├── _02_auto_ownership.qmd # Helper: Automobile Ownership subsection
│   └── _02_cdap.qmd          # Helper: Coordinated Daily Activity Pattern subsection
├── calib_report/        # Installable Python package with report helpers
│   ├── data/            # Data-fetching / cleaning modules (e.g. auto_ownership.py)
│   ├── tables.py        # Table formatting helpers
│   ├── figures.py       # Figure helpers
│   └── pyproject.toml   # Package metadata
├── _book/               # Rendered output (generated)
└── _freeze/             # Quarto freeze cache (generated)
```

## Setup

1. Create the conda environment (installs `calib_report` in editable mode):

   ```powershell
   conda env create -f environment.yaml
   conda activate tm1_calibration_doc
   ```

2. Add your Census API key to a local `.env` file in this folder:

   ```text
   CENSUS_KEY=your_actual_key_here
   ```

   The key is read via `python-dotenv` in `calib_report`. `.env` is git-ignored
   and must never be committed.

3. Install PDF Engine, TinyTex, for PDF rendering:
   ```text
   quarto install tinytex
   ```

## Rendering the report

```powershell
quarto install tinytex
quarto render
```

Output is written to `_book/`. To preview with live reload:

```powershell
quarto preview
```

## The `calib_report` package

`calib_report` is a local package (installed via `-e .` in
`environment.yaml`) that holds reusable code for the report:

- `calib_report.data.*` — fetch and clean source data (Census/ACS, etc.).
- `calib_report.tables` — format DataFrames for Markdown/Quarto display.
- `calib_report.figures` — build charts used in the chapters.

Chapters import from this package so the notebooks stay focused on narrative.

## Helper (include) `.qmd` files

Some chapters are split into smaller, self-contained `.qmd` files that are
pulled in as subsections. These helper files are named with a leading
underscore (e.g. `_02_uwsl.qmd`) so that Quarto treats them as **includes
only** and does not render them as standalone pages or list them in the book
navigation.

A parent chapter defines the section heading and then embeds the helper file
with the [`include` shortcode](https://quarto.org/docs/authoring/includes.html):

```markdown
### Usual Work and School Location Choice
{{< include _02_uwsl.qmd >}}

### Automobile Ownership
{{< include _02_auto_ownership.qmd >}}
```

Current helper files (all live in `chapter/` alongside their parent):

| Helper file | Parent chapter | Subsection |
| --- | --- | --- |
| `_02_uwsl.qmd` | `02-calibration.qmd` | Usual Work and School Location Choice |
| `_02_auto_ownership.qmd` | `02-calibration.qmd` | Automobile Ownership |
| `_02_cdap.qmd` | `02-calibration.qmd` | Coordinated Daily Activity Pattern |

**Conventions**

- Prefix helper files with `_` so Quarto skips them during standalone rendering.
- Name them `_<chapter-number>_<topic>.qmd` to make the parent chapter obvious.
- Do **not** add helper files to the `chapters:` list in `_quarto.yml`; they are
  only referenced through `{{< include >}}`.
- Start headings inside a helper at the level the parent expects (the parent
  supplies the enclosing `###` heading, so helper content usually begins at
  `####` or with body text).
- Keep the include path relative to the parent chapter's folder (`chapter/`).
