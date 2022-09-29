
## Toll calibration

### Background
The toll calibration procedure aims to simulate express lanes dynamic pricing. The procedure runs CTRAMP and highway assignment iteratively until the input toll rates produce a desired level of express lane system performance, i.e. an average speed of 45mph or higher in the time period. It reads the loaded network after highway assignment, and compares the average speed of the express lane facilities (EL) with that of their corresponding general purpose lanes (GL). Further, it classifies each EL facility into five cases, and determines the toll rate adjustment needed for the next iteration (see table below).

| Case #  | EL speed (mph) | GP speed (mph) | Action                                        |
| --------| -------------- |--------------- | --------------------------------------------- |
| Case 1  | <=48**          | any            | EL too slow. Increase toll rate.              |
| Case 2  | >48            | <=40           | GP too slow. Decrease toll rate.              |
| Case 3  | 48-60          | 40-60          | OK. No change in toll.                        |
| Case 4  | >60            | 40-60          | GP speed can be improved. Decrease toll rate. |
| Case 5  | >48            | >60            | Set toll to minimum.                          |
 ** Note: The threshold used in the toll calibration script is 48mph, which is slightly higher than the performance target of 45mph. This is because average speeds in toll calibration runs (which only execute CTRAMP and highway assignment) can be slightly different from the full model run (which includes transit assignment). Setting the threshold slightly higher than the actual performance target makes sure the average speeds in the full model run do not go below 45mph.

In Project Performance Assessment, some additional operational assumptions are made:
1. Minimum toll is 3 cents (2000$) per mile in AM, MD, PM for drive alone and for trucks
2. For selected facilities, two-occupant vehicles always pay half price. For all other facilities, the toll rates for two-occupant vehicles start at 0 in the first iteration; and as the calibration progresses, if drive alone tolls go over $1 per mile, then two-occupant vehiclesis set to half of the drive alone tolls
3. Three-or-more-occupant vehicles use the express lanes for free

A caveat: the speed summary only handles the simple case where a single HOV or express lane link corresponds to a single GP link via a dummy link on each end. This problem applies only a small percentage of links, see discussion in: https://app.asana.com/0/13098083395690/1128985107220991. It takes about 4.5 to 5 hours between iterations on AWS machines (for Back to the Future).


## How to run it?

Step 1: Log on to the aws machine (or server) where the pre-calibration run was completed. Start a new folder with the same name, except that “PreCalib” should be changed to “TollCalib”.

Step 2: Make sure NonDynamicTollFacilities.csv is added under hwy/ and INPUT/hwy (To do: provide more explanation here!)

Step 3: Copy TollCalib_go.batfrom travel-model-one-master on X (\\tsclient\X\travel-model-one-master\utilities\toll_calibration) to this new directory.

This batch file copy the inputs and scripts needed for toll calibration. Users are required to "set" six variables in the batch file (see below).
![Alt text](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/toll_calibration/TollCalib_go_example.PNG "TollCalib_go.bat example")


