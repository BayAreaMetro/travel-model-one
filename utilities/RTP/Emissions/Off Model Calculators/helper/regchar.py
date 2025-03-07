import pandas as pd
import openpyxl

from helper.calcs import OffModelCalculator
class RegionalCharger(OffModelCalculator):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_OffModel_RegionalCharger"
        self.dataFileName="totPopOnly"
        self.strategy="ev charger"

    def update_calculator(self):
        # Step 1: Create run and copy files  
        OffModelCalculator.copy_workbook(self)
        # Step 2: load model data of selected runs
        modelData=OffModelCalculator.get_model_data(self)
        # Step 3: add model data of selected runs to 'Model Data' sheet
        OffModelCalculator.write_model_data_to_excel(self,modelData)
        # Step 4:
        OffModelCalculator.write_runid_to_mainsheet(self)