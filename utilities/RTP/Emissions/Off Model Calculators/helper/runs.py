import os
from templates.external import (
    OFF_MODEL_CALCULATOR_DIR_OUTPUT
    )

def getNextFilePath(output_folder, run):
    
    lastRunId=0
    for f in os.listdir(output_folder):
        fileNameList=f.split("__")
        if f"{fileNameList[0]}__{fileNameList[1]}"== run:
            if int(fileNameList[2])>lastRunId:
                lastRunId=int(fileNameList[2])

        else:
            continue

    return lastRunId + 1

def createNewRun(model_run_ids_list, verbose=False):

    runName=model_run_ids_list[0]+"__"+model_run_ids_list[0]
    pathToRun=f"{OFF_MODEL_CALCULATOR_DIR_OUTPUT}/{runName}__0"

    if not os.path.exists(pathToRun):
        runNameNumber=runName+"__0"
        os.makedirs(pathToRun)
        
    else:
        runID=getNextFilePath(OFF_MODEL_CALCULATOR_DIR_OUTPUT,runName)
        runNameNumber=f"{runName}__{runID}"
        pathToRun=f"{OFF_MODEL_CALCULATOR_DIR_OUTPUT}/{runNameNumber}"
        os.makedirs(pathToRun)

    if verbose:
        print(f"New run created: {runNameNumber}")
        print(f"Location: {pathToRun}")

    return pathToRun