import openpyxl
import pandas as pd
import os

from helper.calcs import OffModelCalculator
class TargetedTransAlt(OffModelCalculator):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_OffModel_TargetedTransAlt"
        self.dataFileName="targetedTransportationAlternatives"
        self.strategy="targeted transportation alternative"

    def get_model_data(self):
        '''This method includes baseline data from the baselineDir
        compared to the one in the super class.'''
        # Get Model Data as df
        rawData=pd.read_csv(
            os.path.join(self.modelDataPath,f"{self.dataFileName}.csv"))
        
        rawData['directory'] = self.runs
        rawData=rawData[['directory', 'variable', 'value']]
        
        # also get 2015 baseline data
        baselineData=pd.read_excel(
            os.path.join('offmodel\\offmodel_output','PBA50+_OffModel_TargetedTransAlt__{}.xlsx'.format(self.runs)), 
            sheet_name='Model Data')
        baselineData = baselineData.loc[baselineData['variable'].isin(['total_households_2015', 'total_jobs_2015'])]
        print('------- check 2015 data: \n{}'.format(baselineData))

        allData = pd.concat([rawData, baselineData])
        print('------- check all data: \n{}'.format(allData))

        if self.verbose:
            print("Unique directories:")
            print(rawData['directory'].unique())

        return allData

    def update_calculator(self):
    
        # Step 1: Create run and copy files  
        OffModelCalculator.copy_workbook(self)
        # Step 2: load and filter model data of selected runs
        modelData=self.get_model_data()
        # Step 3: add model data of selected runs to 'Model Data' sheet
        OffModelCalculator.write_model_data_to_excel(self,modelData)      
        # Step 4:
        OffModelCalculator.write_runid_to_mainsheet(self)