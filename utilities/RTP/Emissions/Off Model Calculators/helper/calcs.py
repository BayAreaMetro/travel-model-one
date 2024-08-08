import shutil
import pandas as pd
import re
import win32com.client
import os
from datetime import datetime


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

    def __init__(self, model_run_id, directory, verbose=False):
        self.uid=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.runs = [model_run_id[0], model_run_id[1]]
        self.pathType=directory
        self.modelDataPath, self.masterFilePath = common.get_directory_constants(self.pathType)
        self.masterWbName=""
        self.dataFileName=""
        self.baselineDir=None
        self.verbose=verbose
        self.varsDir=common.get_vars_directory(self.pathType)
        self.v=OffModelCalculator.get_variable_locations(self)
        
    def copy_workbook(self):
        # Start run
        self.newWbFilePath=common.createNewRun(self)
        
        # make a copy of the workbook
        master_workbook_file = os.path.join(self.masterFilePath,f"{self.masterWbName}.xlsx")
        self.new_workbook_file = os.path.join(self.newWbFilePath,f"{self.masterWbName}__{self.runs[0]}__{self.runs[1]}.xlsx")
        
        
        shutil.copy2(master_workbook_file, self.new_workbook_file)

        if self.verbose:
            print(master_workbook_file)
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
        
        filteredData=rawData.loc[rawData.directory.isin(self.runs+[self.baselineDir])]
        # print(filteredData)
        # Get metadata from model data
        metaData=OffModelCalculator.get_model_metadata(self)
        
        if self.verbose:
            print("Unique directories:")
            print(rawData['directory'].unique())

        return filteredData, metaData

    def get_sb_data(self):
        sbPath=common.get_paths(self.pathType)
        return pd.read_csv(sbPath['SB375'])

    def get_ipa(self, arg):
        name=self.runs[arg]
        pattern = r"(\d{4})_(TM\d{3})_(.*)"
        matches = re.search(pattern, name)

        if matches:
            ipa = matches.group(3)
            year = matches.group(1)

        if self.verbose:
            print(ipa)
        
        return [ipa, int(year)]

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
        
        print(self.new_workbook_file)
        print("File exist?: ",os.path.exists(self.new_workbook_file))
        # print(self.updated_workbook_file)
        
        excel = win32com.client.Dispatch("Excel.Application")
        wb = excel.Workbooks.Open(self.new_workbook_file)
        excel.Visible=True
        wb.RefreshAll()
        wb.SaveAs(self.updated_workbook_file)
        wb.Close()
        excel.Quit()
        
        # Remove old file
        os.remove(self.new_workbook_file)

    # Step 6: log runs in master
        # todo  

    

     
            
            
