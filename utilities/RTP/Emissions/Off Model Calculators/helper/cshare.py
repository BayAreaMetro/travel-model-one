import openpyxl
import pandas as pd

from helper.calcs import OffModelCalculator
class Carshare(OffModelCalculator):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_OffModel_Carshare"
        self.dataFileName="Model Data - Carshare"
        self.strategy="car share"
        self.metaRow=2
        self.dataRow=2

    def write_runid_to_mainsheet(self):
        # get variables location in calculator
        OffModelCalculator.get_variable_locations(self)

        # add run_id to 'Main sheet'
        newWorkbook = openpyxl.load_workbook(self.new_workbook_file)
        mainsheet = newWorkbook['Main sheet']
        modeldatasheet=newWorkbook['Model Data']

        # Select Main sheet variables
        vMS=self.v['Main sheet']

        # Write model data
        mainsheet[vMS['Min_carshare_population_density']]=modeldatasheet[vMS['k_min_pop_density']].value
        # Write run name and year
        mainsheet[vMS['Run_directory']] = self.runs['run']
        mainsheet[vMS['year']] = int(self.runs['year'])
        
        # save file
        newWorkbook.save(self.new_workbook_file)
        newWorkbook.close()

    def get_calculator_names(self):
        log=pd.read_excel(self.masterLogPath
                                 , sheet_name=self.masterWbName
                                 , header=[1]
                                 , skiprows=0
                    )

        return log.columns.tolist()[2:]

    def update_calculator(self):
    
        # Step 1: Create run and copy files  
        OffModelCalculator.copy_workbook(self)

        # Step 2: load and filter model data of selected runs
        modelData, metaData=OffModelCalculator.get_model_data(self)

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
            'daily_vehTrip_reduction': [None],
            'daily_vmt_reduction':[self.rowDict['Out_daily_VMT_reduced'][0]],
            'daily_ghg_reduction':[self.rowDict['Out_daily_GHG_reduced'][0]],
            'strategy':[self.strategy],
            'directory':[folderName],
        }

        df_new=pd.DataFrame(row, index=None)
        df=pd.concat([df,df_new], ignore_index=True)
        df.to_csv(summaryPath, index=False)