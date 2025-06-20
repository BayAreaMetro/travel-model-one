#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import os
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import tempfile
import shutil
import sys

# Add the current directory to the path so we can import the script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import create_tazdata_2020_and_after as script
import common

class TestCreateTazdataScript(unittest.TestCase):
    """Unit tests for create_tazdata_2020_and_after.py"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.year_dir = os.path.join(self.temp_dir, "2020")
        os.makedirs(self.year_dir, exist_ok=True)
    
    def tearDown(self):
        """Tear down test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_map_acs5year_household_income_to_tm1_categories(self):
        """Test mapping household income categories"""
        # Create a fake ACS variable
        acs_var = "acs_5year"
        
        # Call the function from common module
        result = common.map_acs5year_household_income_to_tm1_categories(acs_var)
        
        # Check that result is a DataFrame with expected columns
        self.assertIsInstance(result, pd.DataFrame)
        self.assertIn('incrange', result.columns)
        self.assertIn('HHINCQ', result.columns)
        self.assertIn('share', result.columns)
        
        # Check that all required income quartiles are covered
        self.assertEqual(len(result['HHINCQ'].unique()), 4)
    
    def test_census_to_df(self):
        """Test converting Census API response to DataFrame"""
        # Mock Census API response
        census_resp = [
            {'NAME': 'County 1', 'B01001_001E': 100, 'B01001_002E': 48, 'B01001_026E': 52},
            {'NAME': 'County 2', 'B01001_001E': 200, 'B01001_002E': 96, 'B01001_026E': 104}
        ]
        
        # Call the function from common module
        result = common.census_to_df(census_resp)
        
        # Check that result is a DataFrame with expected columns
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue('NAME' in result.columns or 'NAM' in result.columns)
        self.assertIn('B01001_001', result.columns)  # Suffix should be removed
        
        # Check values
        self.assertEqual(result.loc[0, 'B01001_001'], 100)
        self.assertEqual(result.loc[1, 'B01001_001'], 200)
    
    def test_fix_rounding_artifacts(self):
        """Test fixing rounding artifacts"""
        # Create test DataFrame
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'total': [100, 200, 300],
            'part1': [33.3, 66.7, 100.1],
            'part2': [33.4, 66.6, 99.9],
            'part3': [33.3, 66.7, 100.0]
        })
        
        # Call the function from common module
        result = common.fix_rounding_artifacts(
            df, 'id', 'total', ['part1', 'part2', 'part3'], logging_on=False
        )
        
        # Check that result is a DataFrame with corrected values
        self.assertIsInstance(result, pd.DataFrame)
        
        # Check that sum of parts equals total for each row
        for i in range(len(result)):
            parts_sum = result.loc[i, 'part1'] + result.loc[i, 'part2'] + result.loc[i, 'part3']
            self.assertAlmostEqual(parts_sum, result.loc[i, 'total'], places=5)
    
    def test_scale_data_to_targets(self):
        """Test scaling data to targets"""
        # Create source DataFrame
        source_df = pd.DataFrame({
            'id': [1, 2],
            'total': [100, 200],
            'part1': [30, 70],
            'part2': [30, 70],
            'part3': [40, 60]
        })
        
        # Create target DataFrame
        target_df = pd.DataFrame({
            'id': [1, 2],
            'total_target': [120, 220]
        })
        
        # Call the function from common module
        result = common.scale_data_to_targets(
            source_df, target_df, 'id', 'total', ['part1', 'part2', 'part3'], logging_on=False
        )
        
        # Check that result is a DataFrame with scaled values
        self.assertIsInstance(result, pd.DataFrame)
        
        # Check that total matches target_total
        self.assertEqual(result.loc[0, 'total'], 120)
        self.assertEqual(result.loc[1, 'total'], 220)
        
        # Check that parts sum to total
        for i in range(len(result)):
            parts_sum = result.loc[i, 'part1'] + result.loc[i, 'part2'] + result.loc[i, 'part3']
            self.assertAlmostEqual(parts_sum, result.loc[i, 'total'], places=5)
            
        # Check that parts scaled proportionally
        # First row: parts should be 20% larger
        self.assertAlmostEqual(result.loc[0, 'part1'], 36, places=5)
        self.assertAlmostEqual(result.loc[0, 'part2'], 36, places=5)
        self.assertAlmostEqual(result.loc[0, 'part3'], 48, places=5)
    
    @patch('common.retrieve_census_variables')
    def test_download_acs_blocks(self, mock_retrieve_census):
        """Test downloading ACS block data with mocked Census API"""
        # Mock Census API response
        mock_retrieve_census.return_value = [
            {'STATE': '06', 'COUNTY': '001', 'TRACT': '000100', 'BLOCK': '1000', 'P1_001N': 100},
            {'STATE': '06', 'COUNTY': '001', 'TRACT': '000100', 'BLOCK': '2000', 'P1_001N': 200}
        ]
        
        # Create mock Census client
        mock_census = MagicMock()
        
        # Call the function from common module
        result = common.download_acs_blocks(mock_census, "2020", "dec/pl", states=["06"], counties=["001"])
        
        # Check that retrieve_census_variables was called correctly
        mock_retrieve_census.assert_called_once()
        
        # Check that result is a DataFrame with expected columns
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn('STATE', result.columns)
        self.assertIn('COUNTY', result.columns)
        self.assertIn('TRACT', result.columns)
        self.assertIn('BLOCK', result.columns)
    
    @patch('create_tazdata_2020_and_after.update_tazdata_to_county_target')
    def test_update_gqpop_to_county_totals(self, mock_update):
        """Test updating group quarters population to county totals"""
        # Create source DataFrame
        source_df = pd.DataFrame({
            'TAZ1454': [1, 2, 3],
            'County_Name': ['Alameda', 'Alameda', 'Contra Costa'],
            'gqpop': [100, 200, 300],
            'gq_type_univ': [50, 100, 150],
            'gq_type_mil': [25, 50, 75],
            'gq_type_othnon': [25, 50, 75],
            'AGE0004': [10, 20, 30],
            'AGE0519': [20, 40, 60],
            'AGE2044': [30, 60, 90],
            'AGE4564': [20, 40, 60],
            'AGE65P': [20, 40, 60]
        })
        
        # Create target DataFrame
        target_df = pd.DataFrame({
            'County_Name': ['Alameda', 'Contra Costa'],
            'GQPOP_target': [360, 330]
        })
        
        # Mock ACS_PUMS data
        acs_pums = 2021
        
        # Setup mock for update_tazdata_to_county_target
        mock_update.side_effect = lambda s, t, v, p: s
        
        # Call the function
        result = script.update_gqpop_to_county_totals(source_df, target_df, acs_pums)
        
        # Check that update_tazdata_to_county_target was called at least once
        mock_update.assert_called()
        
        # Check that result has the same shape as the input
        self.assertEqual(len(result), len(source_df))
    
if __name__ == '__main__':
    unittest.main() 