import openpyxl
import pandas as pd

from helper.calcs import OffModelCalculator
class VanPools(OffModelCalculator):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_OffModel_Vanpools"
        self.dataFileName="Model Data - Employer Shuttles"
        self.strategy="vanpool"
        self.metaRow=1
        self.dataRow=1

    def write_runid_to_mainsheet(self):
        # get variables location in calculator
        OffModelCalculator.get_variable_locations(self)
        
        # add run_id to 'Main sheet'
        newWorkbook = openpyxl.load_workbook(self.new_workbook_file)
        mainsheet = newWorkbook['Main sheet']
        
        # Select Main sheet variables
        vMS=self.v['Main sheet']

        # Write run name and year
        mainsheet[vMS['Run_directory_2035']] = self.runs['run']
        mainsheet[vMS['year_a']] = int(self.runs['year'])

        # save file
        newWorkbook.save(self.new_workbook_file)
        newWorkbook.close()

    def update_calculator(self):
    
        # Step 1: Create run and copy files  
        OffModelCalculator.copy_workbook(self)

        # Step 2: load and filter model data of selected runs
        modelData, metaData=OffModelCalculator.get_model_data(self)
        
        # Step 3: add model data of selected runs to 'Model Data' sheet
        if len(modelData)>1:
            OffModelCalculator.write_model_data_to_excel(self,modelData,metaData)
        OffModelCalculator.write_sbdata_to_excel(self)
        
        # Step 4: Write model 
        self.write_runid_to_mainsheet()
        
        # Step 5: open close new wb
        OffModelCalculator.open_excel_app(self)

        # Step 6: update log
        logVariables=self.get_calculator_names()
        OffModelCalculator.log_run(self,logVariables)

    def update_summary_file(self, summaryPath, folderName):
        df=pd.read_csv(summaryPath)
        row={
            'year': [2035, 2050],
            'daily_vehTrip_reduction': [self.rowDict['Vanpool_one_way_vehicle_trip_reductions_2035'][0],
                                        self.rowDict['Vanpool_one_way_vehicle_trip_reductions_2050'][0]],
            'daily_vmt_reduction':[self.rowDict['Out_daily_VMT_reduced_2035'][0],
                                   self.rowDict['Out_daily_VMT_reduced_2050'][0]],
            'daily_ghg_reduction':[self.rowDict['Out_daily_GHG_reduced_2035'][0],
                                   self.rowDict['Out_daily_GHG_reduced_2050'][0]],
            'strategy':[self.strategy,self.strategy],
            'directory':[folderName,folderName],
        }

        df_new=pd.DataFrame(row, index=None)
        df=pd.concat([df,df_new], ignore_index=True)
        df.to_csv(summaryPath, index=False)