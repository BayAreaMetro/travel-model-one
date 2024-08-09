from helper.calcs import OffModelCalculator
class RegionalCharger(OffModelCalculator):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_OffModel_RegionalCharger"
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