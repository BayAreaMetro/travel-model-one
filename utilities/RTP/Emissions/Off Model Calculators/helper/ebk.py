from helper.calcs import OffModelCalculator
import pandas as pd
class EBike(OffModelCalculator):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_OffModel_Ebike"
        self.strategy="electric bike rebates"
        self.dataFileName=None

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
        # Step 2: copy sb375 data
        OffModelCalculator.write_sbdata_to_excel(self)
        # Step 3: open close new wb
        OffModelCalculator.open_excel_app(self)
        # Step 4: update log
        OffModelCalculator.get_variable_locations(self)
        logVariables=self.get_calculator_names()
        OffModelCalculator.log_run(self,logVariables)
    
    def update_summary_file(self, summaryPath, folderName):
        df=pd.read_csv(summaryPath)
        row={
            'year': [2035, 2050],
            'daily_vehTrip_reduction': [None,
                                        None],
            'daily_vmt_reduction': [self.rowDict['Out_daily_VMT_reduced_2035'][0],
                                   self.rowDict['Out_daily_VMT_reduced_2050'][0]],
            'daily_ghg_reduction':[self.rowDict['Out_daily_GHG_reduced_2035'][0],
                                   self.rowDict['Out_daily_GHG_reduced_2050'][0]],
            'strategy':[self.strategy,self.strategy],
            'directory':[folderName,folderName],
        }

        df_new=pd.DataFrame(row, index=None)
        df=pd.concat([df,df_new], ignore_index=True)
        df.to_csv(summaryPath, index=False)