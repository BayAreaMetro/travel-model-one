import pandas as pd
from helper.calcs import OffModelCalculator
class BuyBack(OffModelCalculator):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_OffModel_VehicleBuyback"
        self.strategy="vehicle buy back"
        self.dataFileName=None

    def update_calculator(self):
        # Step 1: Create run and copy files  
        OffModelCalculator.copy_workbook(self)
        # Step 2: copy sb375 data
        OffModelCalculator.write_sbdata_to_excel(self)
        # Step 3: open close new wb
        OffModelCalculator.open_excel_app(self)
        # Step 4: update log
        OffModelCalculator.get_variable_locations(self)
        logVariables=OffModelCalculator.get_calculator_names(self)
        OffModelCalculator.log_run(self,logVariables)

    def update_summary_file(self, summaryPath, folderName):
        df=pd.read_csv(summaryPath)
        row={
            'year': [2035, 2050],
            'daily_vehTrip_reduction': [None,
                                        None],
            'daily_vmt_reduction': [None,
                                    None],
            'daily_ghg_reduction':[self.rowDict['Out_daily_GHG_reduced_2035'][0],
                                   self.rowDict['Out_daily_GHG_reduced_2050'][0]],
            'strategy':[self.strategy,self.strategy],
            'directory':[folderName,folderName],
        }

        df_new=pd.DataFrame(row, index=None)
        df=pd.concat([df,df_new], ignore_index=True)
        df.to_csv(summaryPath, index=False)