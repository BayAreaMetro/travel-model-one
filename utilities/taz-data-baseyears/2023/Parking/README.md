# Parking Cost Estimation

Produces two parking cost fields for all 1,454 Bay Area TAZs, expressed in **year 2000 cents**:

| Field | Meaning | Method |
|---|---|---|
| `OPRKCST` | Hourly (short-term) parking cost | Observed meter data + ML classification for unobserved cities |
| `PRKCST` | Daily/monthly (long-term) parking cost | SpotHero web-scraped rates |

---

## Pipeline

`parking_estimation.py` is the single entry point. It imports and calls `parking_capacity.py` and `parking_published.py` directly at runtime.

The only prerequisite is the SpotHero scrape, which must be run beforehand.  It lives outside this directory, in [tm2py-utils](https://github.com/BayAreaMetro/tm2py-utils/blob/main/tm2py_utils/inputs/land_use/parking_scrape.py).


---

## parking_capacity.py

Allocates block-group-level parking stall counts to TAZ level.

**Sources:**  
[Bay Area Parking Census](https://www.spur.org/publications/spur-report/2022-02-28/bay-area-parking-census), `parking_density_Employee_Capita.shp`,  
Citation:
Mikhail Chester, Alysha Helmrich, and Rui Li. "San Francisco Bay Area Parking Census [Dataset]" Mineta Transportation Institute Publications (2022). doi: https://doi.org/10.31979/mti.2022.2123.ds

**Method:**
- Spatial allocation from block groups to TAZ
- `off_nres` (off-street non-residential stalls): employment-weighted allocation, falls back to area-weighted where block group employment = 0
- `on_all` (on-street, all stall types): area-weighted allocation


---

## parking_published.py

Loads city-published parking meters/rates and spatially assigns them to TAZ as observed OPRKCST.  These are used to train the model in parking estimation step.

**Method:** Area-weighted assignment with a 5% minimum TAZ coverage threshold.  There’s potential for capacity weighting but that may just be burying the area weighting down another level because it requires harmonizing three ways (TAZ x meter area x block group).


**Sources:**

| City | Source | File |
|---|---|---|
| Oakland | [Oakland open data](https://www.oaklandca.gov/Public-Safety-Streets/Transportation-Projects-Reports/Parking-and-Mobility-Related-Maps-and-Data) | `City_of_Oakland_Parking_Meters_20260107.geojson` |
| San Jose | [SJ open data](https://data.sanjoseca.gov/dataset/parking-meters) | `Parking_Meters.geojson` |
| San Francisco (meters) | [SF open data](https://data.sfgov.org/Transportation/Map-of-Parking-Meters/fqfu-vcqd) | `Parking_Meters_20260203.geojson` |
| San Francisco (variable rates) | [SFMTA notices](https://www.sfmta.com/notices/citywide-meter-rate-adjustments) | `January 2026 Parking Meter Rate Change Data.csv` |
| San Francisco (districts) | [SF open data](https://data.sfgov.org/Transportation/Map-of-Parking-Management-Districts/fqfe-qhy8) | `Parking_Management_Districts_20260203.geojson` |
| Berkeley | [ArcGIS portal](https://www.arcgis.com/home/item.html?id=3f718339df3a448e86a4e7474c6bdb85) | `goBerkeley_Areas.shp` |


---

## parking_estimation.py
Main entry point. Produces `parking_costs_taz.csv` and `parking_costs_taz.gpkg`.
### PRKCST (long-term, off-street)
Scraped SpotHero daily/monthly rates (produced by `parking_scrape.py` in [tm2py-utils](https://github.com/BayAreaMetro/tm2py-utils/blob/main/tm2py_utils/inputs/land_use/parking_scrape.py)).  Pre-generated data loaded and merged here.



### OPRKCST (short-term, on-street)

Binary ML classification (paid vs. free) trained on the four observed cities above, applied to all other incorporated cities with on-street capacity. Paid TAZs are assigned the observed median hourly rate (this is an area-weighted value based on TAZ-to-parking area intersection).

By default (no arguments), the script:
- Runs stratified 5-fold cross-validation across all four candidate models: Logistic Regression, Random Forest, Gradient Boosting, SVM (RBF)
- Selects the best model by average CV F1 score
- Uses the CV-derived optimal probability threshold for production predictions



### Running the script

```
python parking_estimation.py [options]
```

| Argument | Default | Description |
|---|---|---|
| `--commercial-density-threshold` | `0.5` | Minimum retail employment density (jobs/acre) for paid parking eligibility. |
| `--force-model` | `None` | Skip auto-selection and force use of `logistic`, `random-forest`, `gradient-boosting`, or `svm`. CV still runs to derive the probability threshold. |
| `--probability-threshold` | `None` (use CV optimal) | Override the CV-derived classification threshold. Only meaningful with `--force-model`. |
| `--max-depth` | `None` (use CV default) | Override tree `max_depth` for the production model when `--force-model` is `random-forest` (CV default 10) or `gradient-boosting` (CV default 5). |

**Examples:**

Run with defaults, CV selects model and threshold automatically:
```
python parking_estimation.py
```

Force a specific model (CV still runs to derive its threshold):
```
python parking_estimation.py --force-model random-forest
```

Force a model and raise the probability threshold to reduce false positives:
```
python parking_estimation.py --force-model random-forest --probability-threshold 0.65
```

Force a shallower tree:
```
python parking_estimation.py --force-model random-forest --max-depth 5
```

Widen the commercial density gate to make more TAZs eligible for prediction:
```
python parking_estimation.py --commercial-density-threshold 0.3
```

### Outputs

| File | Contents |
|---|---|
| `parking_costs_taz.csv` | `TAZ1454`, `OPRKCST`, `PRKCST` (year 2000 cents) |
| `parking_costs_taz.gpkg` | Same columns + `OPRKCST_TYPE`, `PRKCST_TYPE` + geometry |
| `parking_costs_taz_log.txt` | Log |

---


