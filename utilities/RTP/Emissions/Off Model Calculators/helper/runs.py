import os
from helper.mons import get_paths

def getNextFilePath(output_folder, run):
    """
    This method checks for folders with the same name.
    If the folder exists, provides the next number in the sequence.
    """
    
    lastRunId=0
    for f in os.listdir(output_folder):
        fileNameList=f.split("__")
        if f"{fileNameList[0]}__{fileNameList[1]}"== run:
            if int(fileNameList[2])>lastRunId:
                lastRunId=int(fileNameList[2])

        else:
            continue

    return lastRunId + 1

def createNewRun(c, verbose=False):
    """
    Given the two model_run_id_year selected, an output folder is created.
    In this folder, outputs will be saved.
    If the output folder already exists, a sequence is created
    to differentiate outputs.
    """

    path=get_paths(c.pathType)

    runName=c.runs[0]+"__"+c.runs[1]
    pathToRun=os.path.join(path['OFF_MODEL_CALCULATOR_DIR_OUTPUT'],
                           f"{runName}__0")

    if not os.path.exists(pathToRun):
        runNameNumber=runName+"__0"
        os.makedirs(pathToRun)
        
    else:
        runID=getNextFilePath(path['OFF_MODEL_CALCULATOR_DIR_OUTPUT'],runName)
        runNameNumber=f"{runName}__{runID}"
        pathToRun=os.path.join(path['OFF_MODEL_CALCULATOR_DIR_OUTPUT'],
                               runNameNumber)
        os.makedirs(pathToRun)

    if verbose:
        print(f"New run created: {runNameNumber}")
        print(f"Location: {pathToRun}")

    return pathToRun