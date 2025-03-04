import openpyxl
import pandas as pd
import os

from helper.calcs import OffModelCalculator
class TargetedTransAlt(OffModelCalculator):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_OffModel_TargetedTransAlt"
        self.dataFileName="Model Data - Targeted Transportation Alternatives"
        self.strategy="targeted transportation alternative"
        self.metaRow=1
        self.dataRow=1
        self.baselineDir='2015_TM152_IPA_16'

    def get_model_data(self):
        '''This method includes baseline data from the baselineDir
        compared to the one in the super class.'''
        # Get Model Data as df
        rawData=pd.read_csv(
            os.path.join(self.modelDataPath,f"{self.dataFileName}.csv"),
            skiprows=self.dataRow)
        
        filteredData=rawData.loc[rawData.directory.isin([self.runs['run'], self.baselineDir])]
        # Get metadata from model data
        metaData=OffModelCalculator.get_model_metadata(self)
        
        if self.verbose:
            print("Unique directories:")
            print(rawData['directory'].unique())

        return filteredData, metaData

    def write_runid_to_mainsheet(self):
        # get variables location in calculator
        OffModelCalculator.get_variable_locations(self)
        
        # add run_id to 'Main sheet'
        newWorkbook = openpyxl.load_workbook(self.new_workbook_file)
        mainsheet = newWorkbook['Main sheet']
        modeldatasheet=pd.DataFrame(newWorkbook['Model Data'].values)[1:]
        modeldatasheet.columns=modeldatasheet.iloc[0]
        modeldatasheet=modeldatasheet[1:]

        # Select Main sheet variables
        vMS=self.v['Main sheet']

        # Write other variables     
        mainsheet[vMS['Total_households_baseline']]=modeldatasheet.loc[(modeldatasheet.directory==self.baselineDir) \
                                                & (modeldatasheet.variable=='total_households'),'value'].values[0]
        mainsheet[vMS['Total_jobs_baseline']]=modeldatasheet.loc[(modeldatasheet.directory==self.baselineDir) \
                                                & (modeldatasheet.variable=='total_jobs'),'value'].values[0]
        # Write run name and year
        mainsheet[vMS['Run_directory']] = self.runs['run']
        mainsheet[vMS['year']] = int(self.runs['year'])

        # save file
        newWorkbook.save(self.new_workbook_file)
        newWorkbook.close()
    
    def get_calculator_names(self):
        print("sheet name: ", self.masterWbName[:-1])
        log=pd.read_excel(self.masterLogPath
                                 , sheet_name=self.masterWbName[:-1]
                                 , header=[1]
                                 , skiprows=0
                    )

        return log.columns.tolist()[2:]

    def update_calculator(self):
    
        # Step 1: Create run and copy files  
        OffModelCalculator.copy_workbook(self)

        # Step 2: load and filter model data of selected runs
        modelData, metaData=self.get_model_data()

        # Step 3: add model data of selected runs to 'Model Data' sheet
        OffModelCalculator.write_model_data_to_excel(self,modelData,metaData)
        
        # Step 4:
        self.write_runid_to_mainsheet()

        # Step 5: open close new wb
        OffModelCalculator.open_excel_app(self)

        # Step 6: update log
        logVariables=self.get_calculator_names()
        OffModelCalculator.log_run(self,logVariables)
    
    def update_summary_file(self, summaryPath, folderName):
        df=pd.read_csv(summaryPath)
        row={
            'year': [self.runs['year']],
            'daily_vehTrip_reduction': [self.rowDict['Total_daily_trip_reductions'][0]],
            'daily_vmt_reduction':[self.rowDict['Out_daily_VMT_reduced'][0]],
            'daily_ghg_reduction':[self.rowDict['Out_daily_GHG_reduced'][0]],
            'strategy':[self.strategy],
            'directory':[folderName],
        }

        df_new=pd.DataFrame(row, index=None)
        df=pd.concat([df,df_new], ignore_index=True)
        df.to_csv(summaryPath, index=False)