## Generating Peak Hour Excessive Delay (PHED) results

To generate PHED results, you only need to run the wrapper batch script — PHED.bat.

This batch file takes only one argument -- the full file path of the model run output directory on M. Here's an example DOS command:
`X:\travel-model-one-master\utilities\TIP\PHED.bat "M:\Application\Model One\RTP2021\Blueprint\2040_TM152_FBP_Plus_21"`

Note that the double quotes are needed for the argument, because of the blank space between "Model" and "One" on the path

The script takes only a couple of minutes to run. When it's done, the output file can be found in: [the model run output directory on M]\OUTPUT\metrics\federal_metric_PHED.csv

The unit of PHED is "hours of total annual excessive delay per person". More general background about what the PHED metric is can be found at the beginning of the R script that does the main PHED data processing
(https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/TIP/federal_metric_PHED_TM1.5.r#L6-L19).

## Software requirements
- Cube (to export network from cube to shape)
- ArcGIS (because it uses an arcpy script that does spatial joins)
- R-3.5.2 (the script that does the main PHED calculations is written in R) - if you have another version of R installed, edit the R location in the batch script (https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/TIP/PHED.bat#L48)
- map "\\\mainmodel\MainModelShare" as "X:"

## Common error messages 
`RuntimeError: Not signed into Portal.`

Sometimes I get this error message if it has been a while since I last opened ArcGIS Pro. Stackexchange says try reopening ArcGIS Pro and refreshing your connection to the license. See:
https://gis.stackexchange.com/questions/238985/avoiding-arcgisscripting-runtimeerror-not-signed-into-portal-from-arcpy-with-ar

