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
        pathType: where to look for directories. Mtc points to box absolute paths. External to repo relative paths.
        modelDataPath: string, absolute path to model data directory.
        masterFilePath: string, absolute path to offModelCalculators directory.
        masterWbName: string, name of offModelCalculator of interest (e.g. bikeshare)
        dataFileName: string, name of model data file (input).
        verbose: print each method calculations.
        varsDir: master file with all variable locations in all OffModelCalculators.
        v: dictionary, all variable names and values for the OffModelCalculator chosen.
    """

    def __init__(self, model_run_id, directory, uid, verbose=False):
        self.uid=uid
        self.runs = model_run_id
        self.pathType=directory
        self.modelDataPath, self.masterFilePath = common.get_directory_constants(directory)
        self.masterWbName=""
        self.dataFileName=""
        self.baselineDir=None
        self.masterLogPath=common.get_master_log_path(directory)
        self.verbose=verbose
        self.varsDir=common.get_vars_directory(directory)
        
    def copy_workbook(self):
        # Start run
        self.newWbFilePath=common.createNewRun(self)
        
        # make a copy of the workbook
        self.master_workbook_file = os.path.join(self.masterFilePath,f"{self.masterWbName}.xlsx")
        self.new_workbook_file = os.path.join(self.newWbFilePath,f"{self.masterWbName}__{self.runs['run']}.xlsx")
        print("New workbook file")
        print(self.new_workbook_file)

        print("master workbook file")
        print(self.master_workbook_file)
        shutil.copy2(self.master_workbook_file, self.new_workbook_file)

        if self.verbose:
            print(self.master_workbook_file)
            print(self.new_workbook_file)

        # return self.new_workbook_file

    def get_model_metadata(self):
        
        metaData=pd.read_csv(
            os.path.join(self.modelDataPath,f"{self.dataFileName}.csv"),
            nrows=self.metaRow,
            header=None)
        
        if self.verbose:
            print(f"Model Data (R Script) metadata:\n{metaData.columns[0]}")
            
        return metaData

    def get_model_data(self):
        # Get Model Data as df
        rawData=pd.read_csv(
            os.path.join(self.modelDataPath,f"{self.dataFileName}.csv"),
            skiprows=self.dataRow)
        
        filteredData=rawData.loc[rawData.directory.isin([self.runs['run']])]
        # Get metadata from model data
        metaData=OffModelCalculator.get_model_metadata(self)
        
        if self.verbose:
            print("Unique directories:")
            print(rawData['directory'].unique())

        return filteredData, metaData

    def get_sb_data(self):
        sbPath=common.get_paths(self.pathType)
        return pd.read_csv(sbPath['SB375'])

    def write_sbdata_to_excel(self):
        # add sb375 data
        data=OffModelCalculator.get_sb_data(self)
        sbData=data.T.loc[['Year','Population', 'DailyCO2','RunID']]
        with pd.ExcelWriter(self.new_workbook_file, engine='openpyxl', mode = 'a'
                            , if_sheet_exists = 'overlay'
                            ) as writer:  
            sbData.to_excel(writer,
                            sheet_name='SB 375 Calcs',
                            index=False,
                            startcol=1,
                            header=False)
            
        if self.verbose:
            print("Copied SB375 data to excel.")

    def write_model_data_to_excel(self, data, meta):
        
        with pd.ExcelWriter(self.new_workbook_file, engine='openpyxl', mode = 'a', if_sheet_exists = 'replace') as writer:  
        # add metadata
            meta=pd.DataFrame(meta)
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
                        startrow=self.metaRow, startcol=0)
        
        OffModelCalculator.write_sbdata_to_excel(self)

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

    ## Step 5: open/close Excel, autosave
    def open_excel_app(self):
        
        self.updated_workbook_file=os.path.join(self.newWbFilePath,
                                                f"{self.uid.replace(':','--')}__{self.masterWbName}.xlsx")
        
        excel = win32com.client.Dispatch("Excel.Application")
        wb = excel.Workbooks.Open(self.new_workbook_file)
        excel.Visible=True
        wb.RefreshAll()
        wb.SaveAs(self.updated_workbook_file)
        wb.Close()
        
        # Remove old file
        print(f"Trying to remove {self.masterWbName}")
        timesTried=0
        while True:
            try:  
                os.remove(self.new_workbook_file)
                print("Removed")
                break
            except:
                timesTried+=1
                if timesTried<3:
                    time.sleep(8)
                    print("retries: ",timesTried)
                else:
                    print("cannot remove old file.")
                    break

    ##Step 6: log runs in master
    def extract_data_from_mainsheet(self, vNames):
        # Select Main sheet variables
        vMS=self.v['Main sheet']
        
        # open main sheet
        newWorkbook = openpyxl.load_workbook(self.updated_workbook_file,data_only=True)
        mainsheet = newWorkbook['Main sheet']

        # collect data of interest
        data=[]
        data+=[self.uid,self.runs['run']]
        for metric in vNames:
            try:
                data.append(mainsheet[vMS[metric]].value)
                if self.verbose:
                    print(f"Metric: {metric}\nlocation:{vMS[metric]}\nValue: {mainsheet[vMS[metric]].value}")
                
            except:
                print(f"{metric} Not found.")
                pass

        vNames=['Timestamp','directory']+vNames
        self.rowDict=dict(map(lambda i,j : (i,[j]) , vNames,data))
        
        # open output sheet
        log=pd.DataFrame(self.rowDict)

        return log
    
    def check_last_log_index(self):
        if len(self.masterWbName)>31:
            WbName=self.masterWbName[:31]
        else:
            WbName=self.masterWbName
        
        last_entry=pd.read_excel(self.masterLogPath
                                 , sheet_name=WbName
                                 , header=[1]
                                 , usecols=[0]
                                 , skiprows=0
                    )
        if self.verbose:
            print(f"Length of log: {len(last_entry)}")
        
        return len(last_entry)
    
    def get_calculator_names(self):
        log=pd.read_excel(self.masterLogPath
                                 , sheet_name=self.masterWbName
                                 , header=[1]
                                 , skiprows=0
                    )

        return log.columns.tolist()[2:]
    
    def log_run(self, vNames):

        dataTolog=self.extract_data_from_mainsheet(vNames)
        logLength=self.check_last_log_index()

        if len(self.masterWbName)>31:
            WbName=self.masterWbName[:31]
        else:
            WbName=self.masterWbName

        with pd.ExcelWriter(self.masterLogPath, engine='openpyxl', mode = 'a', if_sheet_exists = 'overlay') as writer:  
            # add log to main calc
            dataTolog.to_excel(writer, 
                        sheet_name=WbName, 
                        index=False,
                        header=False,
                        startrow=logLength+2)

    def initialize_summary_file(self, outputPath):
               
        # Create empty summary csv
        header=['year','daily_vehTrip_reduction','daily_vmt_reduction',
                'daily_ghg_reduction','strategy','directory']
        df=pd.DataFrame(columns=header)
        df.to_csv(outputPath, index=False)

    def create_output_summary_path(self,baseRun):
        summaryPath=os.path.join(
                self.paths['OFF_MODEL_CALCULATOR_DIR_OUTPUT']
                , self.uid.replace(':','--')
                , f"off_model_summary_by_strategy_{baseRun}.csv")
        

        return summaryPath

     
            
            
