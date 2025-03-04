import pandas as pd
import openpyxl

from helper.calcs import OffModelCalculator
class RegionalCharger(OffModelCalculator):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_OffModel_RegionalCharger"
        self.strategy="ev charger"
        self.dataFileName=None

    def write_runid_to_mainsheet(self):
        # get variables location in calculator
        OffModelCalculator.get_variable_locations(self)
        
        # add run_id to 'Main sheet'
        newWorkbook = openpyxl.load_workbook(self.new_workbook_file)
        mainsheet = newWorkbook['Main sheet']

        # Select Main sheet variables
        vMS=self.v['Main sheet']

        # Write run year
        mainsheet[vMS['year']] = int(self.runs['year'])

        # save file
        newWorkbook.save(self.new_workbook_file)
        newWorkbook.close()
        
        if self.verbose:
            print(f"Main sheet updated with {self.runs['run']} in location\n{self.new_workbook_file}")

    def update_calculator(self):
        # Step 1: Create run and copy files  
        OffModelCalculator.copy_workbook(self)
        # Step 2: copy sb375 data
        OffModelCalculator.write_sbdata_to_excel(self)
        self.write_runid_to_mainsheet()
        # Step 3: open close new wb
        OffModelCalculator.open_excel_app(self)
        # Step 4: update log
        OffModelCalculator.get_variable_locations(self)
        logVariables=OffModelCalculator.get_calculator_names(self)
        OffModelCalculator.log_run(self,logVariables)

    def update_summary_file(self, summaryPath, folderName):
        df=pd.read_csv(summaryPath)
        row={
            'year': [self.runs['year']],
            'daily_vehTrip_reduction': [None],
            'daily_vmt_reduction': [None],
            'daily_ghg_reduction':[self.rowDict['Out_daily_GHG_reduced'][0]],
            'strategy':[self.strategy],
            'directory':[folderName],
        }

        df_new=pd.DataFrame(row, index=None)
        df=pd.concat([df,df_new], ignore_index=True)
        df.to_csv(summaryPath, index=False)