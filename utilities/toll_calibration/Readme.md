
## Toll calibration

### Background
The toll optimization procedure aims to simulate express lanes dynamic pricing. The procedure runs CTRAMP and highway assignment iteratively until the input toll rates produce a desired level of express lane system performance, i.e. an average speed of targeted speed (such as 45 mph) or higher in the time period. It reads the loaded network after highway assignment, and compares the average speed of the express lane (EL) facilities with that of their corresponding general purpose (GL) lanes. Further, it classifies each EL facility into five cases, and determines the toll rate adjustment needed for the next iteration (see table below).

| Case #  | EL speed (mph)      | GP speed (mph) | Action                                        |
| --------| ------------------- |--------------- | --------------------------------------------- |
| Case 1  | <=THRESHOLD_SPEED*  | any            | EL too slow. Increase toll rate.              |
| Case 2  | >THRESHOLD_SPEED    | <=40           | GP too slow. Decrease toll rate.              |
| Case 3  | THRESHOLD_SPEED-60  | 40-60          | OK. No change in toll.                        |
| Case 4  | >60                 | 40-60          | GP speed can be improved. Decrease toll rate. |
| Case 5  | >THRESHOLD_SPEED    | >60            | Set toll to minimum.                          |

Note * : The THRESHOLD_SPEED used in the toll calibration script is varied by facility, which is defined in [`TOLLCLASS_Designations.xlsx`](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/TOLLCLASS_Designations.xlsx) (column D).

In Project Performance Assessment, some additional operational assumptions are made:
1. The THRESHOLD_SPEED in the toll calibration script is 48 mph, which is slightly higher than the typical express lane performance target of 45 mph. This is because average speeds in toll calibration runs (which only execute CTRAMP and highway assignment) can be slightly different from the full model run (which includes transit assignment). Setting the threshold slightly higher than the actual performance target makes sure the average speeds in the full model run do not go below 45mph.
2. Each facility's maximum toll (dollars per mile in 2000$) in AM, MD, PM for drive alone and for trucks is defined in `TOLLCLASS_Designations.xlsx` (column E). 
3. Each facility's minimum toll (dollars per mile in 2000$) in AM, MD, PM for drive alone and for trucks is defined in `TOLLCLASS_Designations.xlsx` (column F) 
4. For selected facilities, two-occupant vehicles always pay half price. For all other facilities, the toll rates for two-occupant vehicles start at 0 in the first iteration; and as the calibration progresses, if drive alone tolls go over $1 per mile, then two-occupant vehicles is set to half of the drive alone tolls
5. Three-or-more-occupant vehicles use the express lanes for free

It took about 4.5 to 5 hours between iterations on AWS machines (for Back to the Future).


## How to run it?

**A note on file paths**: Sometimes in these batch files or others, a file path is referred to as `\\tsclient\X\rest_of_path`.  This means that the user has mounted their `X` drive onto the machine via *Remote Desktop Connection*.  If the `X` drive is accessible directly (e.g. not from the *Remote Desktop Connection*, then the path would simply say `X:\\rest_of_path`.

1. Log on to the model machine where the pre-calibration run was completed. Start a new folder with the same name, except that `PreCalib` should be changed to `TollCalib`.  For example, if the pre-calibration directory is `2050_TM151_PPA_RT_11_6000_ReX_PreCalib_03`, then the toll calibration directory is `2050_TM151_PPA_RT_11_6000_ReX_TollCalib_03`.

2. Make sure `NonDynamicTollFacilities.csv` exists in `INPUT/hwy` and `hwy` in the pre-calibration run. If `NonDynamicTollFacilities.csv` is missing, copy it from [`NonDynamicTollFacilities.csv`](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/NonDynamicTollFacilities.csv).
(In the future, we will consolidate this file into `tolls.csv`, see [Asana task: "Consolidate the specification of non-dynamically tolled facilities into tolls.csv"](https://app.asana.com/0/1203117570203492/1203219088817572) to reduce the number of input files).  

3. Copy [`TollCalib_go.bat`](TollCalib_go.bat) from this Github directory to this new directory. Note: On MTC servers, the master branch of repository is available in `\\mainmodel\MainModelShare\travel-model-one-master`.

4. Update environment variables in the batch fille. This batch file copies the inputs and scripts needed for toll calibration. Users are required to "set" four variables in the batch file (see below). <br>https://github.com/BayAreaMetro/travel-model-one/blob/a6b8651737ca6138e04b4f35ca8d4cd4ee264521/utilities/toll_calibration/TollCalib_go.bat#L15-L26

    1. Line 15: set the path of the `TOLLCLASS_Designations.xlsx` (required)
    2. Line 18: set the IP address (only needed for aws runs; for runs on MTC servers, leaving this line unchanged or commenting it out would both be fine.)
    3. Line 21: the location of the base run (i.e. pre toll calibration) directory (required)
    4. Line 25: Where do you want the toll calibration outputs to be stored (not required, but MTC staff finds it helpful to have the results automatically copied to the L or M drive) 

5. Run [`TollCalib_go.bat`](TollCalib_go.bat) in the command prompt

For runs on aws, keep the Remote Desktop Connection connected for the duration of the toll calibration run, so results will be automatically copied back to a the drive location specified by the user (`L_DIR` in [`TollCalib_Iterate.bat`](TollCalib_Iterate.bat)).


## Additional tips and tricks
Often, while waiting for the pre-toll-calibration run to complete, analysts may perform further QAQC of the network and correct errors in the network. If the errors are not significant, analysts might choose not to rerun pre-toll-calibration to save time. Instead, analysts might choose to proceed with the toll calibration procedure using the revised network.

In such cases, prior to starting the toll calibration procedure, analysts will need to swap the freeflow.net and tolls.csv in the pre-toll-calibration run (aka the base run). DOS commands to perform such a network swap can be found in [Swab_networks_prior_to_tollcalib.bat](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/toll_calibration/Swab_networks_prior_to_tollcalib.bat).
