import openpyxl

from helper.calcs import Calc

class Bikeshare(Calc):

    def __init__(self,*args, **kwargs):
        super(Bikeshare, self).__init__(*args, **kwargs)
    
    def write_runid_to_mainsheet(self):
        # get variables location in calculator
        v=Calc.get_variable_locations(self)
        print(v)
        
        # add run_id to 'Main sheet'
        newWorkbook = openpyxl.load_workbook(self.new_workbook_file)
        mainsheet = newWorkbook['Main sheet']
        
        # Write run name and year
        cells=['C','D']
        for ix in range(2):
            mainsheet[f'{cells[ix]}14'] = Calc.get_ipa(self, self.runs[ix])[0]
            mainsheet[f'{cells[ix]}15'] = Calc.get_ipa(self, self.runs[ix])[1]


        # save file
        newWorkbook.save(self.new_workbook_file)

        if self.verbose:
            print(f"Main sheet updated with {self.runs} in location\n{self.new_workbook_file}")