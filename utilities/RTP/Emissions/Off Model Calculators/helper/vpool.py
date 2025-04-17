import openpyxl
import pandas as pd
import os

from helper.calcs import OffModelCalculator
class VanPools(OffModelCalculator):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_OffModel_Vanpools"
        self.dataFileName="employerShuttle"
        self.strategy="vanpool"

    def get_model_data(self):
        '''This method includes additional columns
        compared to the one in the super class.'''
        # Get Model Data as df
        rawData=pd.read_csv(
            os.path.join(self.modelDataPath,f"{self.dataFileName}.csv"))
        
        rawData['directory'] = self.runs
        rawData=rawData[['directory', 'simple_mode', 'variable', 'value']]

        return rawData

    def update_calculator(self):
        # Step 1: Create run and copy files  
        OffModelCalculator.copy_workbook(self)
        # Step 2: load and filter model data of selected runs
        modelData=self.get_model_data()
        # Step 3: add model data of selected runs to 'Model Data' sheet
        OffModelCalculator.write_model_data_to_excel(self,modelData)
        # Step 4: Write model 
        OffModelCalculator.write_runid_to_mainsheet(self)