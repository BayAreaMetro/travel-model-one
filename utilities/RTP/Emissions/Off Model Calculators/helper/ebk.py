from helper.calcs import OffModelCalculator

class EBike(OffModelCalculator):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_ModelCalc_CompleteStreets"
        self.dataFileName=None

    def update_calculator(self):
        # Step 1: Create run and copy files  
        OffModelCalculator.copy_workbook(self)
        # Step 2: copy sb375 data
        OffModelCalculator.write_sbdata_to_excel(self)