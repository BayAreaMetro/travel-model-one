import openpyxl
import pandas as pd

from helper.calcs import OffModelCalculator

class Bikeshare(OffModelCalculator):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_OffModel_Bikeshare"
        self.dataFileName="bikeshare"
        self.strategy="bike share"

    def update_calculator(self):
    
        # Step 1: Create run and copy files  
        OffModelCalculator.copy_workbook(self)
        # Step 2: load model data of selected runs
        modelData=OffModelCalculator.get_model_data(self)
        # Step 3: add model data of selected runs to 'Model Data' sheet
        OffModelCalculator.write_model_data_to_excel(self,modelData)       
        # Step 4:
        OffModelCalculator.write_runid_to_mainsheet(self)