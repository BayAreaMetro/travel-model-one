# Metrics

Also known as COBRA metrics, this directoy consists of a set of scripts to calculate intermediate results
for cost/benefit ratio analysis.

Most of the files are run at the end of a model run via [RunMetrics.bat](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/RunMetrics.bat)

## Inputs & Configuration

In addition to reading model output (of course), metrics require a few additional inputs
in `INPUT\metrics`:

  * `BC_config.csv` has scenario specifics (Project ID, Project Name, County, Project Type,
    Project Mode, Costs, Life of Project, and optional baseline directory for comparison)
  * `collisionLookup.csv` maps roadways (indexed by area type, facility type and number of
    lanes) to different rates of fatality, injury or property damage
  * `emissionsLookup.csv` maps VMT (by period, vehicle class and speed) to emissions rates
  * `nodes.xls` is a node lookup for quickboards, mapping node numbers to human-readable names
  * `nonRecurringDelayLookup.csv` maps V/C ratios to delay depending on the number of lanes
  * `Transit Operator LSR VMT Estimates.xlsx` maps transit operator codes to estimates of
    the share of their VMT on local streets & roads (vs highways), as well as
    how that local VMT is distributed by county

### Example `BC_config.csv`

An example baseline config:

```
Project ID,2010_05_XXX
Project Name,2010 Baseline
County,all
Project Type,not applicable
Project Mode,road
Capital Costs (millions of $2013),0
Annual O&M Costs (millions of $2013),0
Farebox Recovery Ratio,0
Life of Project (years),1
Compare,not applicable
```

An example project config:

```
Project ID,2010_05_155
Project Name,2010 Oakland SGR
County,Alameda
Project Type,Pavement
Project Mode,road
Capital Costs (millions of $2013),0
Annual O&M Costs (millions of $2013),0
Farebox Recovery Ratio,0
Life of Project (years),1
percent parking cost incurred in San Francisco,0.5
percent parking cost incurred in Alameda,0.5
percent parking cost incurred in Contra Costa,0.0
percent parking cost incurred in Santa Clara,0.0
percent parking cost incurred in San Mateo,0.0
percent parking cost incurred in Marin,0.0
percent parking cost incurred in Solano,0.0
percent parking cost incurred in Sonoma,0.0
percent parking cost incurred in Napa,0.0
base_dir,M:\Projects\2010_05_XXX\metrics
Compare,scenario-baseline
```

## Output

Intermediate COBRA metrics output can be found in the subdir `metrics` for the model run.
Detailed metrics for the scenario will be summarized in `metrics\BC_[project_id].xlsx`.
This will include metrics for this run and optionally compare those metrics to a base in
order to compute costs and benefits.

Additionally, a (slightly user-unfriendly) text version of these outputs will be written to
`..\all_project_metrics\[project_id].csv`.  The idea here is that a number of scenarios can
be summarized into this directory, and then all of those results can get rolled up into a
single set of files, `..\all_project_metrics\AllProjects_[Data,Desc].csv` by
[rollupAllProjects.py](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/rollupAllProjects.py)

This can be viewed in Tableau using [Cobra Tableau.twb](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/Cobra%20Tableau.twb)

## Output Detail

### Travel Time

#### Auto/Truck (Hours)

These are a simple sum of the vehicle hours traveled summed across all roadway links.
For autos, these are transformed to person hours traveled.  Pulled from the hwy networks
via [hwynet.py](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/hwynet.py).

#### Non-Recurring Freeway Delay (Hours)

One of the required inputs includes `INPUT\metrics\nonRecurringDelayLookup.csv`, which is a lookup
mapping V/C ratio and number of lanes (2 or fewer, 3, or 4 or more) to Non-Recurring
Hours of Delay per Vehicle Miles Traveled.  VMT on each *freeway* link is therefore
multiplied by this lookup to estimate the total Non-Recurring Hours of Delay.  Pulled
from the hwy networks via [hwynet.py](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/hwynet.py).

Note: `nonRecurringDelayLookup.csv` is in vehicle hours but `RunResults.py`(https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/RunResults.py)
transforms these to person hours for auto trips.  This is a *change* from the initial version of cobra.

#### Transit In-Vehicle (Hours)

These are calculated by summing trips times the in-vehicle time for those trips, by
mode.  Calculations are done in [sumTransitTimes.job](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/sumTransitTimes.job)

#### Transit Out-of-Vehicle (Hours)

Similarly, these are colcuated by summing trips times different out-of-vehicle times
for these trips, by mode.  *Walk Access+Egress* includes auxiliary walk time.
*Wait* times include initial wait and transfer wait.  Calculations are done in
[sumTransitTimes.job](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/sumTransitTimes.job)

From the *Plan Bay Area Performance Assessment Report*:

> Differences in benefit valuation for utility-based forecasting (travel model
> logit models) and economic cost-effectiveness evaluation (benefit-cost analysis)
> led to somewhat inconsistent results for mode-switching travelers. This meant
> that, without post-processing, a subset of mode switchers experienced a negative
> benefit from switching to a slower travel time option, even if their utility
> (the basis for the travel modeling choices) was increased. As such, an
> out-of-vehicle transit travel time (OVTT) adjustment factor was applied
> to “zero out” negative OVTT disbenefits from mode switching (projects
> impacted: primarily transit investments).

This can be configured to be based on a single transit mode (one of `com`, `hvy`,
`exp`, `lrf`, or `loc`) or it can be configured to `road`, which means all transit
modes are included

For transit modes, the adjustment is the change in auto trips times
the average out-of-vehicle time per relevant transit trip in the scenario.

For road, the adjustment is the change in transit trips times
the average out-of-vehicle time per transit trip in the scenario.

The idea here is that the change in trips of the opposite mode is a better proxy
for the number of mode-switchers than change in trips for the mode itself, as
the project mode's trips also includes induced travel.

#### Walk/Bike (Hours)

Walk and bike times are based on walk and bike distances transformed to times
assuming a 3 mph walk speed and 12 mph bike speed.  See
[sumNonmotTimes.job](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/sumNonmotTimes.job)

### Travel Cost

#### VMT

This is just the sum of Vehicle Miles Traveled for autos and trucks, tallied by
[hwynet.py](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/hwynet.py)
**This is redundant with Travel Time, above, and there is no need to include in Cost/Benefit sums.  It's included for reference.**

#### Operating Costs

Operating costs for autos and buses come from roadway skims combined with trip tables.
They include pavement costs (repair & maintenance costs and fuel costs, adjusted according
to pavement condition) and they do not include bridge tolls.  See [sumAutoTimes.job](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/sumAutoTimes.job)

Bus operating costs are calculated by [bus_opcost.py](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/bus_opcost.py), which joins roadway
attributes to link-based transit assignment data, and tallies up the VMT the associated
costs with that VMT (from repair & maintenance and fuel expenditure).

**Note:** This is different from previous versions of Cobra, where auto operating cost came directly
from VMT.  The change is due to the fact that TM1 was updated to have operating costs be link-based,
in order to include pavement quality effects.

#### Trips

This section is for **reference**, and doesn't have a monetized cost or benefit associated with it.

#### Parking Costs

Parking costs estimations are not very precise and they rely on the configuration to distinguish
the percent parking cost incurred in XXX county.  Total auto trips are divided up into non-home trips
which are split into work- and non-work trips and multiplied by the configured percent parking cost
incurred in that county.  Each county has an average work and non-work parking cost to monetize
the benefit/cost.

#### Vehicle Ownership (Modeled)

This is the actual vehicle ownership tallied from the [households](http://analytics.mtc.ca.gov/foswiki/Main/Household)
and calculated by the [Auto Ownership Model](http://analytics.mtc.ca.gov/foswiki/Main/ModelSchematic).
Tallied by [tallyAutos.py](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/tallyAutos.py), this only makes sense if the Auto Ownership Model runs for
the scenario, which was not true for Plan Bay Area 2013.  Thus, this is **new and only one Vehicle
Ownership estimation should be used to calculated costs and benefits.**

#### Vehicle Ownership (Est. from Auto Trips)

This is estimated vehicle ownership based on auto trips, annualized, and an assumption of a
fixed number of auto trips per auto.  This is a **legacy measure**, and Modeled Vehicle Ownership
is preferable.

### Air Pollutant

#### PM2.5 (tons)

This is a measure of fine particulates based on VMT from autos and from trucks.

#### CO2 (metric tons)

This is a measure of carbon dioxide emissions based on VMT, vehicle class, time period and vehicle speed.
Tallied by [hwynet.py](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/hwynet.py),
the lookup is specified in `INPUT\metrics\emissionsLookup.csv`.

#### Other

Other emissions are also quantified here, including nitrogen oxides (NOx), sulfur dioxide (SO2)
and a number of [Volatile Organic Compounds (VOCs)](http://en.wikipedia.org/wiki/Volatile_organic_compound).
These measures are also based on VMT, vehicle class, time period and vehicle speed, and lookups are
specified in `INPUT\metrics\emissionsLookup.csv`.

### Collisions, Active Transport & Noise

Fatalities due to collisions, injuries due to collisions and property damage due to collisions are
estimated using a rate of collisions per VMT based on area type, facility type and number of lanes.
These rates are specified in `INPUT\metrics\collisionLookup.csv` and tallied by
[hwynet.py](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/hwynet.py).

#### Trips with Active Transportation

Trips with active transportation are a tally of walk, bike and transit trips.
These are for reference and they are tallied by [sumNonMotTimes.job](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/sumNonMotTimes.job) and
[sumTransitTimes.job](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/sumTransitTimes.job)

#### Avg Minutes Active Tranport per Person

This section is also for reference. It contains a tally of walk and bike times, tallied by
[sumNonMotTimes.job](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/sumNonMotTimes.job), as well as walk time from transit trips (from access, egress
and transfers) tallied by [sumTransitTimes.job](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/sumTransitTimes.job).  The times are summed and then averaged across the
projected population. **TODO: Make projected population configurable.**

#### Active Individuals

Average active minutes per day is multiplied by an estimate of inactive persons to get
total active daily minutes per day by inactive persons.  This is then divided by an
active minute per day requirement to estimate the number of persons who have become active.


#### Noise

The estimation of noise costs are based directly on auto miles and truck miles traveled.
