import shutil
import pandas as pd
import re
import win32com.client
import os
import openpyxl
import time

from helper import common

class OffModelCalculator:
    """
    Off-model calculator general methods to copy, update, and output results
    given two specific model_run_id_year (input).

    Attributes:
        runs: input model_run_id_year in model data input file.
        modelDataPath: string, absolute path to model data directory.
        masterFilePath: string, absolute path to offModelCalculators directory.
        masterWbName: string, name of offModelCalculator of interest (e.g. bikeshare)
        dataFileName: string, name of model data file (input).
        verbose: print each method calculations.
        varsDir: master file with all variable locations in all OffModelCalculators.
        v: dictionary, all variable names and values for the OffModelCalculator chosen.
    """

    def __init__(self, model_run_id, uid, verbose=False):
        self.uid=uid
        self.runs = model_run_id
        self.modelDataPath, self.masterFilePath = common.get_directory_constants()
        self.masterWbName=""
        self.dataFileName=""
        # self.masterLogPath=common.get_master_log_path()
        self.verbose=verbose
        self.varsDir=common.get_vars_directory()
        
    def copy_workbook(self):
        # Start run
        self.newWbFilePath=common.createNewRun(self)
        
        # make a copy of the workbook
        self.master_workbook_file = os.path.join(self.masterFilePath,f"{self.masterWbName}.xlsx")
        self.new_workbook_file = os.path.join(self.newWbFilePath,f"{self.masterWbName}__{self.runs}.xlsx")
        print("New workbook file")
        print(self.new_workbook_file)
        print("master workbook file")
        print(self.master_workbook_file)
        shutil.copy2(self.master_workbook_file, self.new_workbook_file)

        if self.verbose:
            print(self.master_workbook_file)
            print(self.new_workbook_file)

    def get_model_data(self):
        # Get Model Data as df
        rawData=pd.read_csv(
            os.path.join(self.modelDataPath,f"{self.dataFileName}.csv"))

        print('-----------raw model data: \n{}'.format(rawData))
        rawData['directory'] = self.runs
        print('-----------modified model data: \n{}'.format(rawData))
        rawData=rawData[['directory', 'variable', 'value']]
        
        return rawData

    def get_sb_data(self):
        sbPath=common.get_paths()
        return pd.read_csv(sbPath['SB375'])

    def write_sbdata_to_excel(self):
        # add sb375 data
        data=OffModelCalculator.get_sb_data(self)
        sbData=data.set_index('Year')[['Population','DailyCO2','RunID']].T

        with pd.ExcelWriter(self.new_workbook_file, engine='openpyxl', mode = 'a'
                            , if_sheet_exists = 'replace'
                            ) as writer:  
            sbData.to_excel(writer,
                            sheet_name='SB 375 calcs',
                            index=True,
                            startcol=0,
                            header=True)
            
        if self.verbose:
            print("Copied SB375 data to excel.")

    def write_model_data_to_excel(self, data):
        
        with pd.ExcelWriter(self.new_workbook_file, engine='openpyxl', mode = 'a', if_sheet_exists = 'replace') as writer:  
            data.to_excel(writer, 
                        sheet_name='Model Data', 
                        index=False,
                        startrow=0, startcol=3)
        
        OffModelCalculator.write_sbdata_to_excel(self)

    def get_variable_locations(self):

        # allVars=pd.read_excel(self.varsDir)
        allVars=pd.read_csv(self.varsDir)
        calcVars=allVars.loc[allVars.Workbook.isin([self.masterWbName])]
        calcVars=calcVars[['Sheet', 'Variable Name', 'Location_{}'.format(self.runs[:4])]]
        calcVars.rename(columns={'Location_{}'.format(self.runs[:4]): 'Location'}, inplace=True)
        groups=set(calcVars.Sheet)
        self.v={}
        for group in groups:
            self.v.setdefault(group,dict())
            self.v[group]=dict(zip(calcVars['Variable Name'],calcVars['Location']))

        if self.verbose:
            print("Calculator variables and locations in Excel:")
            print(self.v)

    def write_runid_to_mainsheet(self):
        # get variables location in calculator
        OffModelCalculator.get_variable_locations(self)
        
        # add run_id to 'Main sheet'
        newWorkbook = openpyxl.load_workbook(self.new_workbook_file)
        mainsheet = newWorkbook['Main Sheet']

        # Select Main sheet variables
        vMS=self.v['Main Sheet']

        # Write run name and year
        print("-----------running for {}, year {}".format(self.runs, self.runs[:4]))
        mainsheet[vMS['Run_directory']] = self.runs
        mainsheet[vMS['year']] = int(self.runs[:4])

        # save file
        newWorkbook.save(self.new_workbook_file)
        newWorkbook.close()
        
        if self.verbose:
            print(f"Main sheet updated with {self.runs['run']} in location\n{self.new_workbook_file}")
