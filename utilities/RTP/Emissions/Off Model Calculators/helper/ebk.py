from helper.calcs import OffModelCalculator
import pandas as pd
class EBike(OffModelCalculator):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_OffModel_EBIKE"
        self.dataFileName=None

    def get_calculator_names(self):
        log=pd.read_excel(self.master_workbook_file
                                 , sheet_name='Output'
                                 , header=[1]
                                 , skiprows=0
                    )

        return log.columns.tolist()[3:]

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