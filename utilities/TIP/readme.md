To generate PHED results, you only need to run the wrapper batch script — PHED.bat.

This batch file takes only one argument -- the full file path of the model run output directory on M. Here's an example DOS command:
X:\travel-model-one-master\utilities\TIP\PHED.bat "M:\Application\Model One\RTP2021\Blueprint\2040_TM152_FBP_Plus_21"

Note that the double quotes are needed for the argument, because of the blank space between "Model" and "One" on the path

The script takes only a couple of minutes to run. When it's done, the output file can be found in: [the model run output directory on M]\OUTPUT\metrics\federal_metric_PHED.csv
