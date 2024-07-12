import os
import shutil
import pandas as pd
import re
import openpyxl

from helper import runs

def copy_workbook(fileName, masterFilePath, modelRuns, verbose=False):
    # Start run
    newWbFilePath=runs.createNewRun(modelRuns, verbose)
    
    # make a copy of the workbook
    master_workbook_file = f"{masterFilePath}/{fileName}.xlsx"
    new_workbook_file = f"{newWbFilePath}/{fileName}__{modelRuns[0]}__{modelRuns[1]}.xlsx"
    
    shutil.copy2(master_workbook_file, new_workbook_file)

    if verbose:
        print(master_workbook_file)
        print(new_workbook_file)

    return new_workbook_file

def get_model_metadata(inputDataPath, inputDataFileName, verbose=False):
    metaData=pd.read_csv(
        f"{inputDataPath}/{inputDataFileName}.csv",
        nrows=0)
    
    if verbose:
        print(f"Model Data (R Script) metadata:\n{metaData.columns[0]}")
        
    return metaData.columns[0]

def get_model_data(inputDataPath, inputDataFileName, modelRuns, verbose=False):
    # Get Model Data as df
    rawData=pd.read_csv(
        f"{inputDataPath}/{inputDataFileName}.csv",
        skiprows=1)
    
    filteredData=rawData.loc[rawData.directory.isin(modelRuns)]

    # Get metadata from model data
    metaData=get_model_metadata(inputDataPath, inputDataFileName, verbose)
    
    if verbose:
        print("Unique directories:")
        print(rawData['directory'].unique())

    return filteredData, metaData

def get_ipa(arg, verbose=False):

    pattern = r"(\d{4})_(TM\d{3})_(.*)"
    matches = re.search(pattern, arg)

    if matches:
        ipa = matches.group(3)
        year = matches.group(1)

    if verbose:
        print(ipa)
    
    return [ipa, int(year)]

def write_model_data_to_excel(wbPath, data, meta, verbose=False):
    
    with pd.ExcelWriter(wbPath, engine='openpyxl', mode = 'a', if_sheet_exists = 'replace') as writer:  
    # add metadata
        meta=pd.DataFrame([meta])
        meta.to_excel(writer, 
                      sheet_name='Model Data', 
                      index=False,
                      header=False, 
                      startrow=0, startcol=0)
    with pd.ExcelWriter(wbPath, engine='openpyxl', mode = 'a', if_sheet_exists = 'overlay') as writer:  
    # add model data
    # this only works with pandas=1.4.3 or later; in earlier version, it will not overwrite sheet, but add new one with sheet name 'Model Data1'
        data.to_excel(writer, 
                      sheet_name='Model Data', 
                      index=False, 
                      startrow=1, startcol=0)
    
    if verbose:
        print(f"Metadata: {meta}")

def write_runid_to_mainsheet(wbPath, modelRuns, verbose=False):
    # add run_id to 'Main sheet'
    newWorkbook = openpyxl.load_workbook(wbPath)
    mainsheet = newWorkbook['Main sheet']
    
    # Run name and year
    mainsheet['C14'] = get_ipa(modelRuns[0])[0]
    mainsheet['C15'] = get_ipa(modelRuns[0])[1]
    mainsheet['D14'] = get_ipa(modelRuns[1])[0]
    mainsheet['D15'] = get_ipa(modelRuns[1])[1]

    # save file
    newWorkbook.save(wbPath)

    if verbose:
        print(f"Main sheet updated with {modelRuns} in location\n{wbPath}")