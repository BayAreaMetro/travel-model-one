import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path
import logging
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Import the calibration framework
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calibration_framework import CalibrationBase, create_histogram_tlfd

# Import the calibration framework
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calibration_framework import CalibrationBase, create_histogram_tlfd



class WorkSchoolLocationCalibration(CalibrationBase):
    """Calibration processor for usual work and school location."""
    
    def __init__(self, config_file: str = None):
        super().__init__("01", config_file)
    
    def process_data(self) -> dict:
        """Process the usual work and school location data."""
        # Load input data
        taz_data = pd.read_csv(self.config.get('data_sources', 'taz_data'))
        wsloc_results = pd.read_csv(self.submodel_config['input_file'])
        
        # Load distance skim - this may be different for BATS
        dist_skim = pd.read_csv(self.config.get('data_sources', 'dist_skim'),
                               names=['orig', 'dest', 'ones', 'DIST'])
        dist_skim = dist_skim.drop('ones', axis=1)
        

        # Get county lookup
        logging.info("Loading input data files...")
        lookup_county = self.config.get_county_lookup()

        
        # Add Home COUNTY
        home_taz_county = taz_data[['ZONE', 'COUNTY']].rename(columns={'ZONE': 'HomeTAZ'})
        wsloc_results = wsloc_results.merge(home_taz_county, on='HomeTAZ', how='left')
        wsloc_results = wsloc_results.merge(lookup_county, on='COUNTY', how='left')
        wsloc_results = wsloc_results.rename(columns={'COUNTY': 'HomeCOUNTY', 'county_name': 'Home_county_name'})
        logging.info("Input data loaded. Processing county lookup...")
        
        # Add Work COUNTY
        work_taz_county = taz_data[['ZONE', 'COUNTY']].rename(columns={'ZONE': 'WorkLocation'})
        wsloc_results = wsloc_results.merge(work_taz_county, on='WorkLocation', how='left')
        wsloc_results = wsloc_results.merge(lookup_county, on='COUNTY', how='left')
        wsloc_results = wsloc_results.rename(columns={'COUNTY': 'WorkCOUNTY', 'county_name': 'Work_county_name'})
        
        logging.info("Merging Home COUNTY data...")
        # Process county summary
        wsloc_county = wsloc_results.groupby(['Home_county_name', 'Work_county_name']).size().reset_index(name='num_pers')
        wsloc_county['num_pers'] = wsloc_county['num_pers'] / self.sampleshare
        wsloc_county_spread = wsloc_county.pivot(index='Home_county_name', columns='Work_county_name', values='num_pers')
        wsloc_county_spread = wsloc_county_spread.fillna(0).reset_index()
        logging.info("Merging Work COUNTY data...")
        
        # If BATS Data, process distance differently
        # TODO: Find BATS Data
        # If distance is included in the data file, ignore the attach skims step steps

        # Process trip length distributions and averages - only need to do this for the model results
        logging.info("Processing county summary...")
        trip_types = ['work', 'univ', 'school']
        trip_tlfd_results = {}
        avg_trip_lengths = []
        
        for trip_type in trip_types:
            # Filter data based on trip type
            if trip_type == 'work':
                trip_dists = wsloc_results[wsloc_results['WorkLocation'] > 0][
                    ['Home_county_name', 'EmploymentCategory', 'HomeTAZ', 'WorkLocation']].copy()
                trip_dists = trip_dists.merge(
                    dist_skim.rename(columns={'orig': 'HomeTAZ', 'dest': 'WorkLocation'}),
                    on=['HomeTAZ', 'WorkLocation'], how='left')
            elif trip_type == 'univ':
                trip_dists = wsloc_results[
                    (wsloc_results['SchoolLocation'] > 0) & 
                    (wsloc_results['StudentCategory'] == "College or higher")
                ][['Home_county_name', 'StudentCategory', 'HomeTAZ', 'SchoolLocation']].copy()
                trip_dists = trip_dists.merge(
                    dist_skim.rename(columns={'orig': 'HomeTAZ', 'dest': 'SchoolLocation'}),
                    on=['HomeTAZ', 'SchoolLocation'], how='left')
            elif trip_type == 'school':
                trip_dists = wsloc_results[
                    (wsloc_results['SchoolLocation'] > 0) & 
                    (wsloc_results['StudentCategory'] == "Grade or high school")
                ][['Home_county_name', 'StudentCategory', 'HomeTAZ', 'SchoolLocation']].copy()
                trip_dists = trip_dists.merge(
                    dist_skim.rename(columns={'orig': 'HomeTAZ', 'dest': 'SchoolLocation'}),
                    on=['HomeTAZ', 'SchoolLocation'], how='left')
            
            # Calculate trip length frequency distribution
            trip_tlfd = pd.DataFrame({'distbin': range(1, 151)})
            
            # Process by county
            for county in lookup_county['county_name']:
                county_trip_dists = trip_dists[trip_dists['Home_county_name'] == county]
                
                if len(county_trip_dists) > 0:
                    hist_df = create_histogram_tlfd(county_trip_dists['DIST'], sampleshare=self.sampleshare)
                    # Remove county prefix for column name
                    col_name = county
                    hist_df = hist_df.rename(columns={'count': col_name})
                    trip_tlfd = trip_tlfd.merge(hist_df, on='distbin', how='left')
                    
                    # Add to average trip lengths
                    avg_trip_lengths.append({
                        'county': col_name,
                        'trip_type': trip_type,
                        'mean_trip_length': county_trip_dists['DIST'].mean()
                    })
            
            # Total across all counties
            if len(trip_dists) > 0:
                hist_df = create_histogram_tlfd(trip_dists['DIST'], sampleshare=self.sampleshare)
                hist_df = hist_df.rename(columns={'count': 'Total'})
                trip_tlfd = trip_tlfd.merge(hist_df, on='distbin', how='left')
                
                avg_trip_lengths.append({
                    'county': 'Total',
                    'trip_type': trip_type,
                    'mean_trip_length': trip_dists['DIST'].mean()
                })
            
            # Reorder columns and fill NaN
            county_cols = sorted([col for col in trip_tlfd.columns if col not in ['distbin', 'Total']])
            col_order = ['distbin'] + county_cols + (['Total'] if 'Total' in trip_tlfd.columns else [])
            trip_tlfd = trip_tlfd[col_order].fillna(0)
            
            trip_tlfd_results[trip_type] = trip_tlfd
        
        # Process average trip lengths
        avg_trip_lengths_df = pd.DataFrame(avg_trip_lengths)
        avg_triplen_spread = avg_trip_lengths_df.pivot(index='county', columns='trip_type', values='mean_trip_length')
        avg_triplen_spread = avg_triplen_spread.reset_index()
        
        # Reorder columns
        desired_cols = ['county'] + [col for col in ['work', 'univ', 'school'] if col in avg_triplen_spread.columns]
        avg_triplen_spread = avg_triplen_spread[desired_cols]
        
        return {
            'county_summary': wsloc_county_spread,
            'trip_tlfd_work': trip_tlfd_results.get('work'),
            'trip_tlfd_univ': trip_tlfd_results.get('univ'),
            'trip_tlfd_school': trip_tlfd_results.get('school'),
            'avg_trip_lengths': avg_triplen_spread
        }
    
    def generate_outputs(self, results: dict):
        """Generate output files and Excel updates."""
        # County summary
        county_file = self.save_csv(results['county_summary'], 
                                   f"{self.submodel}_usual_work_school_location_TM_county.csv")
        self.write_dataframe_to_sheet(results['county_summary'], start_row=4, start_col=1,
                                     source_row=1, source_col=1, source_text=f"Source: {county_file}")
        
        # Trip length frequency distributions
        trip_types = [('work', 1), ('univ', 14), ('school', 27)]
        for trip_type, col in trip_types:
            if results[f'trip_tlfd_{trip_type}'] is not None:
                logging.info("Generating output files and Excel updates...")
                tlfd_file = self.save_csv(results[f'trip_tlfd_{trip_type}'], 
                                         f"{self.submodel}_usual_work_school_location_TM_{trip_type}_TLFD.csv")
                self.write_dataframe_to_sheet(results[f'trip_tlfd_{trip_type}'], start_row=19, start_col=col,
                                             source_row=17, source_col=col, source_text=f"Source: {tlfd_file}")
        
        # Average trip lengths
        avg_file = self.save_csv(results['avg_trip_lengths'], 
                                f"{self.submodel}_usual_work_school_location_TM_avgtriplen.csv")
        self.write_dataframe_to_sheet(results['avg_trip_lengths'], start_row=4, start_col=14,
                                     source_row=3, source_col=14, source_text=f"Source: {avg_file}")


def main():
    """Main entry point for the usual work and school location calibration."""
    logging.info("Starting usual work and school location calibration...")
    calibration = WorkSchoolLocationCalibration()
    calibration.run()
    logging.info("Calibration complete.")


if __name__ == "__main__":
    main()

