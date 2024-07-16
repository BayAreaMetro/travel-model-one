'''
Class for the common calculator methods.
'''
import shutil
import pandas as pd
import re

from helper import (mons,runs)


class Calc:

    def __init__(self, args, verbose=False):
        self.runs = [args.model_run_id_2035, args.model_run_id_2050]
        self.modelDataPath, self.masterFilePath = mons.get_directory_constants(args.d)
        self.masterWbName=""
        self.dataFileName=""
        self.verbose=verbose
        self.varsDir=mons.get_vars_directory(args.d)
        self.v=Calc.get_variable_locations(self)
        
    def copy_workbook(self):
        # Start run
        newWbFilePath=runs.createNewRun(self.runs)
        
        # make a copy of the workbook
        master_workbook_file = f"{self.masterFilePath}/{self.masterWbName}.xlsx"
        self.new_workbook_file = f"{newWbFilePath}/{self.masterWbName}__{self.runs[0]}__{self.runs[1]}.xlsx"
        
        
        shutil.copy2(master_workbook_file, self.new_workbook_file)

        if self.verbose:
            print(master_workbook_file)
            print(self.new_workbook_file)

        return self.new_workbook_file

    def get_model_metadata(self):
        metaData=pd.read_csv(
            f"{self.modelDataPath}/{self.dataFileName}.csv",
            nrows=0)
        
        if self.verbose:
            print(f"Model Data (R Script) metadata:\n{metaData.columns[0]}")
            
        return metaData.columns[0]

    def get_model_data(self):
        # Get Model Data as df
        rawData=pd.read_csv(
            f"{self.modelDataPath}/{self.dataFileName}.csv",
            skiprows=1)
        
        filteredData=rawData.loc[rawData.directory.isin(self.runs)]

        # Get metadata from model data
        metaData=Calc.get_model_metadata(self)
        
        if self.verbose:
            print("Unique directories:")
            print(rawData['directory'].unique())

        return filteredData, metaData

    def get_ipa(self, arg):

        pattern = r"(\d{4})_(TM\d{3})_(.*)"
        matches = re.search(pattern, arg)

        if matches:
            ipa = matches.group(3)
            year = matches.group(1)

        if self.verbose:
            print(ipa)
        
        return [ipa, int(year)]

    def write_model_data_to_excel(self, data, meta):
        
        with pd.ExcelWriter(self.new_workbook_file, engine='openpyxl', mode = 'a', if_sheet_exists = 'replace') as writer:  
        # add metadata
            meta=pd.DataFrame([meta])
            meta.to_excel(writer, 
                        sheet_name='Model Data', 
                        index=False,
                        header=False, 
                        startrow=0, startcol=0)
        with pd.ExcelWriter(self.new_workbook_file, engine='openpyxl', mode = 'a', if_sheet_exists = 'overlay') as writer:  
        # add model data
        # this only works with pandas=1.4.3 or later; in earlier version, it will not overwrite sheet, but add new one with sheet name 'Model Data1'
            data.to_excel(writer, 
                        sheet_name='Model Data', 
                        index=False, 
                        startrow=1, startcol=0)
        
        if self.verbose:
            print(f"Metadata: {meta}")

    def get_variable_locations(self):

        allVars=pd.read_excel(self.varsDir)
        calcVars=allVars.loc[allVars.Workbook.isin([self.masterWbName])].drop(columns=['Workbook','Description'])
        groups=set(calcVars.Sheet)
        self.v={}
        for group in groups:
            self.v.setdefault(group,dict())
            self.v[group]=dict(zip(calcVars['Variable Name'],calcVars['Location']))
        
        if self.verbose:
            print("Calculator variables and locations in Excel:")
            print(self.v)

     
            
            
