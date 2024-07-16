import openpyxl

from helper.calcs import Calc

class Bikeshare(Calc):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_OffModel_Bikeshare"
        self.dataFileName="Model Data - Bikeshare"
    
    def write_runid_to_mainsheet(self):
        # get variables location in calculator
        Calc.get_variable_locations(self)
        
        # add run_id to 'Main sheet'
        newWorkbook = openpyxl.load_workbook(self.new_workbook_file)
        mainsheet = newWorkbook['Main sheet']

        # Select Main sheet variables
        vMS=self.v['Main sheet']

        # Write run name and year
        mainsheet[vMS['Run_directory_2035']] = Calc.get_ipa(self, self.runs[0])[0]
        mainsheet[vMS['Run_directory_2050']] = Calc.get_ipa(self, self.runs[1])[0]
        mainsheet[vMS['year_a']] = Calc.get_ipa(self, self.runs[0])[1]
        mainsheet[vMS['year_b']] = Calc.get_ipa(self, self.runs[1])[1]


        # save file
        newWorkbook.save(self.new_workbook_file)

        if self.verbose:
            print(f"Main sheet updated with {self.runs} in location\n{self.new_workbook_file}")

    def update_calculator(self):
    
        # Step 1: Create run and copy files  
        Calc.copy_workbook(self)

        # Step 2: load and filter model data of selected runs
        modelData, metaData=Calc.get_model_data(self)

        # Step 3: add model data of selected runs to 'Model Data' sheet
        Calc.write_model_data_to_excel(self,modelData,metaData)
        
        # Step 4:
        self.write_runid_to_mainsheet()

        ## Step 5: open/close Excel, autosave
        # todo
        # 
        # Step 6: log runs in master
        # todo   