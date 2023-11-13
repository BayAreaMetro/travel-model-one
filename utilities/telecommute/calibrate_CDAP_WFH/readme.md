
###Background: 

Previously in TM1.5 the WFH workers were modelled within the CDAP universe. With the new "Simple WFH model" in TM1.6, WFH workers are taken out of the CDAP universe so we need more of the remaining workers to travel to work. This calibration ensured the number of workers going to work remain unchanged between TM1.5 and TM1.6.
 
This is achieved by two additional constants in the Coordinated Daily Activity Pattern (CDAP) Model
They are in row 86 and 87 in CoordinatedDailyActivityPattern.xls
* "Adjustment to FT workers (since WFH people are already taken out of the universe so we want more of the remaining people to travel to work)"
* "Adjustment to PT workers (since WFH people are already taken out of the universe so we want more of the remaining people to travel to work)"

###Calibration approach: 

To calibrate, we only need to run core from the beginnng up to CDAP. This means editing CTRAMP\runtime\mtcTourBased.properties to turn off model components after CDAP.
 
Additionally, to speed things up, again in mtcTourBased.properties we feed it the best ShadowPrice.Input.File we have. And we turn UsualWorkAndSchoolLocationChoice.ShadowPricing.MaximumIterations = 1. The example mtcTourBased.properties is included in the current subdirectory.

Furthermore, to further speed things up, each calibration run uses a 20% sample only (see : SAMPLESHARE=0.20).

After each calibration iteration, we calculated the change in the constant = ln(target/modelled) 

For MTC internal use: 
* The spreadsheet summarizing the results of each calibration iteration is in: M:\Application\Model One\RTP2025\IncrementalProgress\validation_targets\2015_WorkersTravelingToWork.xlsx.
* The Tableau workbook that summarizes the CDAP results across different calibration run is in: M:\Application\Model One\RTP2025\IncrementalProgress\across_runs\across_RTP2025_IP_cdapResults.twb
* Asana task: https://app.asana.com/0/0/1205704508591537/f