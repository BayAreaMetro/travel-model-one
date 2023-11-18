# Interregional Travel

This folder contains material relevant to interriegional travel, also known as internal/external travel, or ix-ex.

## Process documentation

Asana task history (internal-only):
* [Oct 2023: Update interregional highway travel assumptions](https://app.asana.com/0/1204085012544660/1203759802600901/f)
* [Feb 2021: Interregional travel assumption...](https://app.asana.com/0/310827677834656/1199962632605860/f)
* [Nov 2019: Modify interregional volumes and finalize for PBA50](https://app.asana.com/0/403262763383022/1107875685875486/f)
* [Dec 2018: Horizon Futures IX/EX inputs](https://app.asana.com/0/403262763383021/802137197128986/f)

### Preprocessing

1. [`create_ix_2015.job`](create_ix_2015.job) was used to create the 2015 base year input table.
    * Summary: Created the 2015 base year table using [Interregional Volumes v3 (integrating SACOG feedback).xlsx](https://mtcdrive.box.com/s/1v6my109gjxq7v7kxc9j63sumzie9jbw). This file was created/updated for the 2021 RTP, or Plan Bay Area 2050.
    * Input: 
        * `M:\Development\Travel Model One\InternalExternal\ixDaily2006x4.may2208.mat`
    * Output:
        * `ixDaily2005.tpp`, matrices: ix_daily_da, ix_daily_sr2, ix_daily_sr3, ix_daily_total
        * `ixDaily2015.tpp`, matrices: ix_daily_da, ix_daily_sr2, ix_daily_sr3, ix_daily_total
        * `ixDaily2005_totals.dbf`, fields: EXT_ZONE, PROD, ATTR
        * `ixDaily2015_totals.dbf`, fields: EXT_ZONE, PROD, ATTR

2. [`create_ix_2021.job`](create_ix_2021.job) was used ot create the 2021 base year input table.
    * Summary: Created the 2015 base year table using [MTC_Interregional Volumes pba50+_v2.xlsx](https://mtcdrive.box.com/s/agq4nyowcdpdb2udf2v2s3j1j32fazva). It just scales the 2015 table based on the 2021 gateway total volumes. This file was created/updated for the 2025 RTP, or Plan Bay Area 2050+.
    * See also: [MTC_Gateway Volume Forecast Methodology.docx](https://mtcdrive.box.com/s/q98g43riir786lhq19xa3w99tyzh8dsh)
    * Input:
        * `M:\Development\Travel Model One\InternalExternal\RTP2021_PBA50\ixDaily2015.tpp`, matrices: ix_daily_da, ix_daily_sr2, ix_daily_sr3, ix_daily_total
        * `ixDaily2015_totals.dbf`, fields: EXT_ZONE, PROD, ATTR
        * [`totals_baseyears.dbf`](totals_baseyears.dbf), fields: EXT_ZONE,TOTAL_2015,TOTAL_2021
    * Output:
        * `ixDaily2021.tpp`, matrices: ix_daily_da, ix_daily_sr2, ix_daily_sr3, ix_daily_total
        * `ixDaily2021_totals.dbf`, fields: EXT_ZONE, PROD, ATTR

### Model Process
Every iteration before assignment, the following scripts are run:

1. [`IxForecasts_horizon.job`](../../model-files/scripts/nonres/IxForecasts_horizon.job)
    * Summary: This script takes a base year (2015) daily trip matrix makes the following assumptions:
        * For `FUTURE`==`PBA50`, assumes the non-commute share grows based on the configured slope.
        * For `FUTURE`==`CleanAndGreen`, assumes no growth from 2015.
        * For `FUTURE`==`BackToTheFuture`, assumes the total share grows based on the configured slope, with the slope adjusted upwards by 50% for gateways to the south and east.
        * For `FUTURE`==`RisingTidesFallingFortunes`, assumes the total share grows based on the configured slope.
        * Additionally, the script handles the external-to-extnernal trips between zones 1461 and 1462.
    * Input: 
        * Environment variable, `MODEL_YEAR`: a number higher than 2015
        * Environment variable, `FUTURE`: one of `PBA50`,`CleanAndGreen`,`BackToTheFuture`, or `RisingTidesFallingFortunes`
        * `nonres\ixDaily2015.tpp`, matrices: ix_daily_da, ix_daily_sr2, ix_daily_sr3, ix_daily_total
        * `nonres\ixDaily2015_totals.dbf`, fields: EXT_ZONE, PROD, ATTR.  These are the total daily trips produced and attracted to each external zone.
        * `nonres\ixex_config.dbf`, fields: EXT_ZONE, comm_share (commute share), slope
    * Output:
        * `nonres\ixDailyx4.tpp`, fields: ix_daily_da, ix_daily_sr2, ix_daily_sr3, ix_daily_total. This is a forecast-year specific trip table containing internal/external, external/internal, and external/external vehicle travel.

2. [`IxTimeOfDay.job`](../../model-files/scripts/nonres/IxTimeOfDay.job)
    * Summary: Applies diurnal factors to the daily estimate of internal/external personal vehicle trips. Also moves some trips to truck trip tables.
    * Input:
        * `nonres\ixDailyx4.tpp`, fields: ix_daily_da, ix_daily_sr2, ix_daily_sr3, ix_daily_total
    * Output:
        * `nonres\ixDailyx4_truck.tpp`, fields: vsm_daily, sml_daily, med_daily, lrg_daily
        * `nonres\tripsIx[EA,AM,MD,PM,EV]x.tpp`: fields: DA, S2, S3

3. [`IxTollChoice.job`](../../model-files/scripts/nonres/IxTollChoice.job)
    * Summary: Applies binomial choice model to auto internal/external personal vehicle travel.
    * Input:
        * `nonres\tripsIx[EA,AM,MD,PM,EV]x.tpp`, fields: DA, S2, S3
        * `nonres\tripsHsr[EA,AM,MD,PM,EV].tpp`, fields: DA_VEH, SR2_VEH
        * `skims\hwyskm[EA,AM,MD,PM,EV].tpp`, matrices: [TOLL?]TIME[DA,S2,S3],[TOLL?]DIST[DA,S2,S3], [TOLL?]BTOLL[DA,S2,S3], TOLLVTOLL[DA,S2,S3]
        * `ctramp\scripts\block\hwyparam.block`: for auto operating cost
    * Output:
        *  `nonres\tripsIx[EA,AM,MD,PM,EV].tpp`, fields : DA, SR2, SR3, DATOLL, SR2TOLL, SR3TOLL

## Gateway Nodes


|	Gateway ID	|	Gateway	|
| ------------- | --------- |
|	1455	|	State Route 1 (Sonoma)	|
|	1456	|	State Route 128 (Sonoma)	|
|	1457	|	U.S. Route 101 (Sonoma)	|
|	1458	|	State Route 29 (Napa)	|
|	1459	|	State Route 128 (Solano)	|
|	1460	|	Interstate 505 (Solano)	|
|	1461	|	State Route 113 (Solano)	|
|	1462	|	Interstate 80 (Solano)	|
|	1463	|	State Route 12 (Solano)	|
|	1464	|	State Route 160 (Contra Costa)	|
|	1465	|	State Route 4 (Contra Costa)	|
|	1466	|	County Route J-4 (Contra Costa)	|
|	1467	|	Interstate 205 + Interstate 580 (Alameda)	|
|	1468	|	State Route 152 (Santa Clara/East)	|
|	1469	|	State Route 156 (Santa Clara)	|
|	1470	|	State Route 25 (Santa Clara)	|
|	1471	|	U.S. Route 101 (Santa Clara)	|
|	1472	|	State Route 152 (Santa Clara/West)	|
|	1473	|	State Route 17 (Santa Clara)	|
|	1474	|	State Route 9 (Santa Clara)	|
|	1475	|	State Route 1 (San Mateo)	|
