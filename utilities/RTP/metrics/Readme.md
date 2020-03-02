# Metrics

Also known as COBRA (COst Benefits Results Analyzer) metrics, this directoy consists of a set of scripts to calculate intermediate results for cost/benefit ratio analysis.

Most of the files are run at the end of a model run via [RunMetrics.bat](../RunMetrics.bat)

## Table of Contents
  * [Inputs & Configuration](#inputs--configuration)
    * [Example `BC_config.csv`](#example-bc_configcsv)
  * [Output](#output)
  * [Output Detail](#output-detail)
    * [Travel Time & Cost](#travel-time--cost)
    * [Travel Time (Legacy)](#travel-time-legacy)
    * [Travel Cost (Legacy)](#travel-cost-legacy)
    * [Air Pollutant](#air-pollutant)
    * [Collisions, Active Transport & Noise](#collisions-active-transport--noise)
    
    
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
Capital Costs (millions of $2017),0
Annual O&M Costs (millions of $2017),0
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
Capital Costs (millions of $2017),0
Annual O&M Costs (millions of $2017),0
Farebox Recovery Ratio,0
Life of Project (years),1
base_dir,M:\Projects\2010_05_XXX\metrics
Compare,scenario-baseline
Zero Negative Logsum TAZs,"1-190"
Zero Logsum TAZs,500
```

Note that the last two lines, `Zero Negative Logsum TAZs` and `Zero Logsum TAZs` is _optional_ and should be used only
when investigations have concluded that a modeling limitation is affecting the logsum diffs inappropriately.
(For example, inconsistencies in path finding weights and utility weights might cause logsums to decrease slightly even
if all we're doing is increasing transit frequency.)  If it's used, a README file will be required to be present to
explain why it's there.

## Output

Intermediate COBRA metrics output can be found in the subdir `metrics` for the model run.
Detailed metrics for the scenario will be summarized in `metrics\BC_[project_id].xlsx`.
This will include metrics for this run and optionally compare those metrics to a base in
order to compute costs and benefits.

Additionally, a (slightly user-unfriendly) text version of these outputs will be written to
`..\all_project_metrics\[project_id].csv`.  The idea here is that a number of scenarios can
be summarized into this directory, and then all of those results can get rolled up into a
single set of files, `..\all_project_metrics\AllProjects_[Data,Desc].csv` by
[rollupAllProjects.py](rollupAllProjects.py)

This can be viewed in Tableau using [Cobra Tableau.twb](Cobra%20Tableau.twb)

## Output Detail

### Travel Time & Cost

#### Logsum Hours

This is a measure based on the [Rule of one-half](http://en.wikipedia.org/wiki/Economic_surplus#Rule_of_one-half)
as it applies to change in consumer surplus:

Change in Consumer Surplus = 0.5(Q<sub>1</sub> + Q<sub>0</sub>)(P<sub>1</sub> - P<sub>0</sub>)

where

 * Q<sub>0</sub> and Q<sub>1</sub> are, respectively, the quantity demanded before and after a change in supply
 * P<sub>0</sub> and P<sub>1</sub> are, respectively, the prices before and after a change in supply

Thus, for CoBRA analysis, the scenario is the change in supply and the

Change in Consumer Surplus = 0.5(T<sub>base</sub> + T<sub>scenario</sub>)(L<sub>scenario</sub> - L<sub>base</sub>)

where

 * T<sub>base</sub> and T<sub>scenario</sub> are, respectively, persons traveling in the base and scenario model runs
 * L<sub>base</sub> and L<sub>scenario</sub> are, respectively, the destination choice logsums transformed to person hours in the base and scenario model runs

Mandatory and non-mandatory logsums are computed by [RunAccessibility.bat](../../../model-files/RunAccessibility.bat).
Mandatory logsums use AM Peak period skims, and non-mandatory logsums use MD period skims.
Mandatory logsums are applied to workers and students, and non-mandatory logsums are applied to all persons; these
accessibility markets are tallied by [AccessibilityMarkets.Rmd](../../../model-files/scripts/core_summaries/AccessibilityMarkets.Rmd)

##### Cliff Effect Mitigation for logsum_diff_minutes

Logsums are susceptible to cliff effects in path-finding because they reflect modes appearing/disappearing even if the utility
of those modes aren't great.

For example, if some TAZs previously had 39.9 minute drive access to transit in the baseline and cross over to 40.01 minutes
of drive access; they could lose a drive-to-transit mode which would give them a small negative logsum difference, which is really
not representative of an actual change in accessibility, but will affect the logsum and then get multiplied out by the
TAZ population, which may be large.  The effect of this differs from model noise, because model noise will effect the Consumer Surplus
both negativley and positively and roughly add up to zero, while the cliff effects can switch on in one direction and bias the
Consumer Surplus in a nontrivial way (either positively or negatively).

To mitigate this, we do the following process: For logsum diffs with a relative low absolute value magnitude (10% of the
maximum absolute value logsum diff), we'll suppress these with a smooth dampening function.  This leaves the higher magnitude logsum
differences alone but dampens out the small ones.

#### Societal Benefits

Since the logsums include costs as seen by the user (traveler), it includes things like fares
and tolls which are transfers.

Components:

  * Transit Fares: trips x transit skims (calculated by [sumTransitTimes.job](sumTransitTimes.job))
  * Auto Households - Bridge Tolls: trips x auto skims (calculated by [sumAutoTimes.job](sumAutoTimes.job))
  * Auto Households - Value Tolls: trips x auto skims (calculated by [sumAutoTimes.job](sumAutoTimes.job))

#### Non-Recurring Freeway Delay (Hours)

One of the required inputs includes `INPUT\metrics\nonRecurringDelayLookup.csv`, which is a lookup
mapping V/C ratio and number of lanes (2 or fewer, 3, or 4 or more) to Non-Recurring
Hours of Delay per Vehicle Miles Traveled.  VMT on each *freeway* link is therefore
multiplied by this lookup to estimate the total Non-Recurring Hours of Delay.  Pulled
from the hwy networks via [hwynet.py](hwynet.py).

Note: `nonRecurringDelayLookup.csv` is in vehicle hours but [RunResults.py](RunResults.py)
transforms these to person hours for auto trips.  This is a *change* from the initial version of cobra.

#### Non-Household

Components:

  * Time - Truck (Computed VHT)
  * Cost - Auto ($2000) - IX/EX: See [Operating Costs section](#operating-costs)
  * Cost - Auto ($2000) - AirPax: See [Operating Costs section](#operating-costs)
  * Cost - Truck ($2000) - Computed: See [Operating Costs section](#operating-costs)
  * Time - Auto (PHT) - IX/EX: Calculated using Internal/External trip tables and skims via [sumAutoTimes.job](sumAutoTimes.job)
  * Time - Auto (PHT) - AirPax: Calculated using airport trip tables and skims via [sumAutoTimes.job](sumAutoTimes.job)

### Travel Time (Legacy)

:exclamation: This section is legacy and has been replaced with the methodology in **Travel Time & Cost**, above.

#### Auto/Truck (Hours)

These are a simple sum of the vehicle hours traveled summed across all roadway links.
For autos, these are transformed to person hours traveled.  Pulled from the hwy networks
via [hwynet.py](hwynet.py).  Since these come from networks, they include nonresident trips
(intra-regional and air passenger trips).

#### Non-Recurring Freeway Delay 

See [section above](#non-recurring-freeway-delay-hours), in the **Travel Time & Cost** section.

#### Transit In-Vehicle (Hours)

These are calculated by summing trips times the in-vehicle time for those trips, by
mode.  Calculations are done in [sumTransitTimes.job](sumTransitTimes.job)

#### Transit Out-of-Vehicle (Hours)

Similarly, these are colcuated by summing trips times different out-of-vehicle times
for these trips, by mode.  *Walk Access+Egress* includes auxiliary walk time.
*Wait* times include initial wait and transfer wait.  Calculations are done in
[sumTransitTimes.job](sumTransitTimes.job)

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
[sumNonmotTimes.job](sumNonmotTimes.job)

### Travel Cost (Legacy)

:exclamation: This section is legacy and has been replaced with the methodology in **Travel Time & Cost**, above.

#### VMT

This is just the sum of Vehicle Miles Traveled for autos and trucks, tallied by
[hwynet.py](hwynet.py)
**This is redundant with Travel Time, above, and there is no need to include in Cost/Benefit sums.  It's included for reference.**

#### Operating Costs

Operating costs for autos come from roadway skims combined with trip tables.
They include pavement costs (repair & maintenance costs and fuel costs, adjusted according
to pavement condition) and they do not include bridge tolls.  See [sumAutoTimes.job](sumAutoTimes.job)

Internal/External trips (_IX/EX_) and airport trips (_AirPax_) have their own trip tables.

_Truck - Computed_ - comes from truck volumes in the baseline network, scaled up by the increase in
auto VMT, and multiplied by the truck operating cost for the roadway link.  (So this metric is calculated
from the roadway network rather than from skims.)

_Truck - Modeled_ is calculated similarly except the truck volumes for the scenario are used directly
from the model.  This is just for comparison, but it's not used because we don't trust the modeled
truck VMT sensitivity.

**Note:** This is different from previous versions of Cobra, where auto operating cost came directly
from VMT.  The change is due to the fact that TM1 was updated to have operating costs be link-based,
in order to include pavement quality effects.

#### Trips

This section is for **reference**, and doesn't have a monetized cost or benefit associated with it.

#### Parking Costs

Parking costs estimations are based on tours, with tour duration multiplied by the configured hourly parking cost (either PRKCST or OPRKCST; 
see [tazdata](http://analytics.mtc.ca.gov/foswiki/Main/TazData) for more detail).  Additionally, some workers have subsidized work parking 
(see `fp_choice` in [the Persons data](http://analytics.mtc.ca.gov/foswiki/Main/Person)).  See [tallyParking.py](tallyParking.py)

#### Vehicle Ownership (Modeled)

This is the actual vehicle ownership tallied from the [households](http://analytics.mtc.ca.gov/foswiki/Main/Household)
and calculated by the [Auto Ownership Model](http://analytics.mtc.ca.gov/foswiki/Main/ModelSchematic).
Tallied by [tallyAutos.py](tallyAutos.py), this only makes sense if the Auto Ownership Model runs for
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
Tallied by [hwynet.py](hwynet.py),
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
[hwynet.py](hwynet.py).

#### Trips with Active Transportation

Trips with active transportation are a tally of walk, bike and transit trips.
These are for reference and they are tallied by [sumNonMotTimes.job](sumNonMotTimes.job) and
[sumTransitTimes.job](sumTransitTimes.job)

#### Avg Minutes Active Tranport per Person

This section is also for reference. It contains a tally of walk and bike times, tallied by
[sumNonMotTimes.job](sumNonMotTimes.job), as well as walk time from transit trips (from access, egress
and transfers) tallied by [sumTransitTimes.job](sumTransitTimes.job).  The times are summed and then averaged across the
projected population.

#### Active Individuals

Average active minutes per day is multiplied by an estimate of inactive persons to get
total active daily minutes per day by inactive persons.  This is then divided by an
active minute per day requirement to estimate the number of persons who have become active.


#### Noise

The estimation of noise costs are based directly on auto miles and truck miles traveled.
