
## Toll calibration

### Background
The toll calibration procedure aims to simulate express lanes dynamic pricing. The procedure runs CTRAMP and highway assignment iteratively until the input toll rates produce a desired level of express lane system performance, i.e. an average speed of targeted speed (such as 45 mph) or higher in the time period. It reads the loaded network after highway assignment, and compares the average speed of the express lane facilities (EL) with that of their corresponding general purpose lanes (GL). Further, it classifies each EL facility into five cases, and determines the toll rate adjustment needed for the next iteration (see table below).

| Case #  | EL speed (mph)   | GP speed (mph) | Action                                        |
| --------| ---------------- |--------------- | --------------------------------------------- |
| Case 1  | <=TARGET_SPEED*  | any            | EL too slow. Increase toll rate.              |
| Case 2  | >TARGET_SPEED    | <=40           | GP too slow. Decrease toll rate.              |
| Case 3  | TARGET_SPEED-60  | 40-60          | OK. No change in toll.                        |
| Case 4  | >60              | 40-60          | GP speed can be improved. Decrease toll rate. |
| Case 5  | >TARGET_SPEED    | >60            | Set toll to minimum.                          |

Note * : The TARGET_SPEED used in the toll calibration script is varied by facility, which is defined in [TOLLCLASS_Designations.xlsx](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/TOLLCLASS_Designations.xlsx) (column D).

In Project Performance Assessment, some additional operational assumptions are made:
1. Each facility's maximum toll (dollars per mile in 2000 $) in AM, MD, PM for drive alone and for trucks is defined in TOLLCLASS_Designations.xlsx (column E). 
2. Each facility's minimum toll (dollars per mile in 2000 $) in AM, MD, PM for drive alone and for trucks is defined in TOLLCLASS_Designations.xlsx (column F) 
3. For selected facilities, two-occupant vehicles always pay half price. For all other facilities, the toll rates for two-occupant vehicles start at 0 in the first iteration; and as the calibration progresses, if drive alone tolls go over $1 per mile, then two-occupant vehiclesis set to half of the drive alone tolls
4. Three-or-more-occupant vehicles use the express lanes for free

A caveat: the speed summary only handles the simple case where a single HOV or express lane link corresponds to a single GP link via a dummy link on each end. This problem applies only a small percentage of links, see discussion in: https://app.asana.com/0/13098083395690/1128985107220991. It takes about 4.5 to 5 hours between iterations on AWS machines (for Back to the Future).


## How to run it?

Step 1: Log on to the aws machine where the pre-calibration run was completed. Start a new folder with the same name, except that “PreCalib” should be changed to “TollCalib”. (If the pre-calibration run was done on a local server e.g. model2-a,b,c,d then this can be done from any of the local servers.)

e.g. 2050_TM151_PPA_RT_11_6000_ReX_PreCalib_03 --> 2050_TM151_PPA_RT_11_6000_ReX_TollCalib_03

Step 2: Make sure NonDynamicTollFacilities.csv is added under hwy/ and INPUT/hwy of the pre-calibration run. If NonDynamicTollFacilities.csv is missing, bring it from [NonDynamicTollFacilities.csv](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/NonDynamicTollFacilities.csv).
(In the future, we will consolidate this file into tolls.csv, see https://app.asana.com/0/1203117570203492/1203219088817572 to make the process more smooth).  

Step 3: Copy TollCalib_go.bat from travel-model-one-master on X drive (\\tsclient\X\travel-model-one-master\utilities\toll_calibration) to this new directory. The path could also be X:\travel-model-one-master\utilities\toll_calibration, depending on your computer environment.

This batch file copy the inputs and scripts needed for toll calibration. Users are required to "set" four variables in the batch file (see below).
![Alt text]([https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/toll_calibration/TollCalib_go_withComfigurableSpeedandToll_example.PNG](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/toll_calibration/TollCalib_go_withComfigurableSpeedandToll_example.PNG) "TollCalib_go_withComfigurableSpeedandToll_example")

Line 15: set the path of the TOLLCLASS_Designations.xlsx (requied)

Line 18: set the IP address (most likely no need to change)

Line 21: the location of the base run (i.e. pre toll calibration) directory 

Line 25: Where do you want the toll calibration outputs to be stored on L drive.

Be aware that Ling 42-Line 50 (https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/toll_calibration/TollCalib_go.bat#L42-L50), the path could be X:\travel-model-one-master\utilities\toll_calibration without the word " \\tsclient\". If needed, change to the correct path.


Step 4: launch tollcalib_go.bat using the command prompt

For runs on aws, keep the Remote Desktop Connection connected for the duration of the toll calibration run. Results will be automatically copied back to a L drive location specified by the user (L_DIR in TollCalib_Iterate.bat).


