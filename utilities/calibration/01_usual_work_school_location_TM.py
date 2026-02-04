
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


class WorkSchoolLocationCalibration(CalibrationBase):
    """Calibration processor for usual work and school location."""
    
    def __init__(self, config_file: str = None):
        if config_file is None:
            # Default to config file in the same directory as this script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(script_dir, 'calibration_config.yaml')
        super().__init__("01", config_file)
    
    def process_data(self) -> dict:
        """Process the usual work and school location data."""
        # Load input data
        taz_data = pd.read_csv(self.config.get('data_sources', 'taz_data'))
        wsloc_results = pd.read_csv(self.submodel_config['input_file'])
        
        # Load distance skim
        dist_skim = pd.read_csv(self.config.get('data_sources', 'dist_skim'), header=0,
                               usecols = ['orig', 'dest', 'DIST'])
        
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
        
        # Attach distances from distance skim
        logging.info("Attaching work distances...")
        work_dist = dist_skim.rename(columns={'orig': 'HomeTAZ', 'dest': 'WorkLocation', 'DIST': 'WorkDist'})
        wsloc_results = wsloc_results.merge(work_dist, on=['HomeTAZ', 'WorkLocation'], how='left')
        
        logging.info("Attaching school distances...")
        school_dist = dist_skim.rename(columns={'orig': 'HomeTAZ', 'dest': 'SchoolLocation', 'DIST': 'SchoolDist'})
        wsloc_results = wsloc_results.merge(school_dist, on=['HomeTAZ', 'SchoolLocation'], how='left')
        
        # Save enhanced wsloc_results with distances
        wsloc_with_dist_file = f"{self.output_dir}/wsloc_results_with_distances.csv"
        wsloc_results.to_csv(wsloc_with_dist_file, index=False)
        logging.info(f"Saved wsloc results with distances to {wsloc_with_dist_file}")

        logging.info("Merging Home COUNTY data...")
        # Process county summary
        wsloc_county = wsloc_results.groupby(['Home_county_name', 'Work_county_name']).size().reset_index(name='num_pers')
        wsloc_county['num_pers'] = wsloc_county['num_pers'] / self.sampleshare
        wsloc_county_spread = wsloc_county.pivot(index='Home_county_name', columns='Work_county_name', values='num_pers')
        wsloc_county_spread = wsloc_county_spread.fillna(0).reset_index()
        logging.info("Merging Work COUNTY data...")

        

        # Process trip length distributions and averages
        logging.info("Processing trip length distributions...")
        trip_types = ['work', 'univ', 'school']
        trip_tlfd_results = {}
        avg_trip_lengths = []
        
        for trip_type in trip_types:
            # Filter data based on trip type and use attached distances
            if trip_type == 'work':
                trip_dists = wsloc_results[wsloc_results['WorkLocation'] > 0][
                    ['Home_county_name', 'EmploymentCategory', 'WorkDist']].copy()
                trip_dists = trip_dists.rename(columns={'WorkDist': 'DIST'})
            elif trip_type == 'univ':
                trip_dists = wsloc_results[
                    (wsloc_results['SchoolLocation'] > 0) & 
                    (wsloc_results['StudentCategory'] == "College or higher")
                ][['Home_county_name', 'StudentCategory', 'SchoolDist']].copy()
                trip_dists = trip_dists.rename(columns={'SchoolDist': 'DIST'})
            elif trip_type == 'school':
                trip_dists = wsloc_results[
                    (wsloc_results['SchoolLocation'] > 0) & 
                    (wsloc_results['StudentCategory'] == "Grade or high school")
                ][['Home_county_name', 'StudentCategory', 'SchoolDist']].copy()
                trip_dists = trip_dists.rename(columns={'SchoolDist': 'DIST'})
            
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
        bats_data = self.submodel_config.get("bats_data")
        logging.info("Generating output files and Excel updates...")

        if (bats_data):
            trip_types = [('work', 2), ('univ', 15), ('school', 28)]
            for trip_type, col in trip_types:
                if results[f'trip_tlfd_{trip_type}'] is not None:

                    tlfd_file = f"{self.output_dir}/BATS_Summaries/{trip_type}TLFD.csv"
                    results[f'trip_tlfd_{trip_type}'].to_csv(tlfd_file, index = False)
                    self.write_dataframe_to_sheet(results[f'trip_tlfd_{trip_type}'], start_row= 4,  start_col=col, sheet_name="CHTS TLFD",
                                                source_row=1, source_col=col, source_text=f"Source: {tlfd_file}")
                    
                    logging.info(f"Saving trip length frequency distributions for {trip_type} to {tlfd_file}")     
        
            # Average trip lengths
            avg_length_file = f"{self.output_dir}/BATS_Summaries/AvgTripLen.csv"
            results['avg_trip_lengths'].to_csv(avg_length_file, index = False)
            self.write_dataframe_to_sheet(results['avg_trip_lengths'], start_row=3, start_col=1, sheet_name="CHTS AvgTripLen",
                                        source_row=1, source_col=1, source_text=f"Source: {avg_length_file}")
            logging.info(f"Saving average trip lengths to {avg_length_file}")     

                
        else: 
            # County summary
            logging.info("Generating output files and Excel updates...")

            county_file = f"{self.output_dir}/{self.submodel}_usual_work_school_location_TM_county.csv"

            results['county_summary'].to_csv(county_file, index = False)
            
            self.write_dataframe_to_sheet(results['county_summary'], start_row=4, start_col=1,
                                        source_row=1, source_col=1, source_text=f"Source: {county_file}")

            logging.info(f"Saving county summary to {county_file}")            
            # Trip length frequency distributions
            trip_types = [('work', 1), ('univ', 14), ('school', 27)]
            for trip_type, col in trip_types:
                if results[f'trip_tlfd_{trip_type}'] is not None:

                    tlfd_file = f"{self.output_dir}/{self.submodel}_usual_work_school_location_TM_{trip_type}_TLFD.csv"
                    results[f'trip_tlfd_{trip_type}'].to_csv(tlfd_file, index = False)
                    self.write_dataframe_to_sheet(results[f'trip_tlfd_{trip_type}'], start_row=19, start_col=col,
                                                source_row=17, source_col=col, source_text=f"Source: {tlfd_file}")
                    logging.info(f"Saving trip length frequency distributions for {trip_type} to {tlfd_file}")            

            # Average trip lengths
            avg_length_file = f"{self.output_dir}/{self.submodel}_usual_work_school_location_TM_avgtriplen.csv"
            results['avg_trip_lengths'].to_csv(avg_length_file, index = False)
            self.write_dataframe_to_sheet(results['avg_trip_lengths'], start_row=4, start_col=14,
                                        source_row=3, source_col=14, source_text=f"Source: {avg_length_file}")
            logging.info(f"Saving average trip lengths to {avg_length_file}")            
            


def main():
    """Main entry point for the usual work and school location calibration."""
    logging.info("Starting usual work and school location calibration...")
    calibration = WorkSchoolLocationCalibration()
    calibration.run()
    logging.info("Calibration complete.")


if __name__ == "__main__":
    main()

