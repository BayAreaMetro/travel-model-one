
# Regional Transit Fares

This is the implementation of a regional transit fare, which is typically distance-based and covers a subset of [Transit Modes](https://github.com/BayAreaMetro/modeling-website/wiki/TransitModes).

The implementation is as follows:

1. In transit skimming, skim one additional matrix called distRegFar, which is the distance travelled on any of the transit modes included in the strategy
2. In SetUpModel.bat, if this strategy is active, [`apply_regional_transit_fares_to_skims.job`](apply_regional_transit_fares_to_skims.job) should be copied into `CTRAMP\scripts\skims`
3. Directly after transit skimming, if the aformentioned file is present, it will be run to modify the fare matrices in the transit skims based on the transit distance travelled by the given modes (to trigger the fare adjustment), using the total transit distance travelled (to determine the fare).

## Project history:
* 2019 PPA: [Integrated Transit Fare System](https://app.asana.com/0/741988522701299/956015808600228/f)
* 2020 PBA50: [T4 - Reform Regional Transit Fare Policy (TM1.5)](https://app.asana.com/0/403262763383022/1188775845203250/f)
* 2025 PBA50+: [T2: Fare integration (Improve the Rider Experience through Transit Network Integration)](https://app.asana.com/0/1204085012544660/1208431274924535/f)