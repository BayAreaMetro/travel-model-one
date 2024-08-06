import openpyxl

from helper.calcs import OffModelCalculator

class Carshare(OffModelCalculator):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.masterWbName="PBA50+_OffModel_Carshare"
        self.dataFileName="Model Data - Carshare"
        self.metaRow=2
        self.dataRow=2

    def write_runid_to_mainsheet(self):
        # get variables location in calculator
        OffModelCalculator.get_variable_locations(self)

        # add run_id to 'Main sheet'
        newWorkbook = openpyxl.load_workbook(self.new_workbook_file)
        mainsheet = newWorkbook['Main sheet']
        modeldatasheet=newWorkbook['Model Data']

        # Select Main sheet variables
        vMS=self.v['Main sheet']

        # Write model data
        mainsheet[vMS['Min_carshare_population_density']]=modeldatasheet[vMS['k_min_pop_density']].value
        # Write run name and year
        mainsheet[vMS['Run_directory_2035']] = OffModelCalculator.get_ipa(self, 0)[0]
        mainsheet[vMS['Run_directory_2050']] = OffModelCalculator.get_ipa(self, 1)[0]
        mainsheet[vMS['year_a']] = OffModelCalculator.get_ipa(self, 0)[1]
        mainsheet[vMS['year_b']] = OffModelCalculator.get_ipa(self, 1)[1]
        
        # save file
        newWorkbook.save(self.new_workbook_file)


    def update_calculator(self):
    
        # Step 1: Create run and copy files  
        OffModelCalculator.copy_workbook(self)

        # Step 2: load and filter model data of selected runs
        modelData, metaData=OffModelCalculator.get_model_data(self)

        # Step 3: add model data of selected runs to 'Model Data' sheet
        OffModelCalculator.write_model_data_to_excel(self,modelData,metaData)
        
        # Step 4:
        self.write_runid_to_mainsheet()

    