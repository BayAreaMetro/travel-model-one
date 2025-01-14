import pandas as pd
import unittest
from unittest import TestCase

# Case 1: Data and formulas update correctly
# This script checks that the Excel workbook
# opens and closes. Then, checks formulas are updated.
# Only checks for bike_share calculator.

class TestFormulaUpdate(TestCase):
    def read_data_sb375(self,path):
        wb=pd.ExcelFile(path)
        data=pd.read_excel(wb,'SB 375 Calcs')

        # print(data)
        return data

    def read_data_mainsheet(self,path):
        wb=pd.ExcelFile(path)
        data=pd.read_excel(wb,'Main sheet',
                        skiprows=22,
                        nrows=2,
                        header=None)
        # print(data)
        return data

    def read_bikeshare(self,path):
        sb=self.read_data_sb375(path)
        main=self.read_data_mainsheet(path)

        return sb,main

    def test_bike_share(self, verbose=False):

        PATH=r'C:\Users\63330\Documents\projects\MTC\travel-model-one\utilities\RTP\Emissions\Off Model Calculators\models\PBA50+_OffModel_Bikeshare.xlsx'
        OUTPUT=r'C:\Users\63330\Documents\projects\MTC\travel-model-one\utilities\RTP\Emissions\Off Model Calculators\data\output\2035_TM160_IPA_16__2035_TM152_FBP_Plus_24__14\2024-08-08 10--14--23__PBA50+_OffModel_Bikeshare.xlsx'
        sbOrigin,mainOrigin=self.read_bikeshare(PATH)
        sbDest,mainDest=self.read_bikeshare(OUTPUT)

        passed=self.assertEqual(
            mainDest.iloc[1][2],
            -.00009525782551264607,
            msg="Equal"
        )

        if passed==None:
            print("Passed Case 1")

        if verbose:
            print("SB 375 Calcs")
            print("Cells updated: ",sbOrigin.iloc[1][2005]!=sbDest.iloc[1][2005])
            print("Correct value: ", sbDest.iloc[1][2005]==61020)

            print("Main sheet")
            print("Cells updated: ",mainOrigin.iloc[1][2]!=mainDest.iloc[1][2])
            print("Correct value: ", mainOrigin.iloc[1][2], " - ", mainDest.iloc[1][2])

caseOne=TestFormulaUpdate()
caseOne.test_bike_share()