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
from calibration_framework import CalibrationBase, create_histogram_tlfd, add_county_info
from calibration_data_models import (
    CountySummary,
    TripLengthFrequency,
    AverageTripLength,
    validate_dataframe
)

class WorkSchoolLocationCalibration(CalibrationBase):
    """Calibration processor for usual work and school location."""
    
    def __init__(self, config_file: str = None):
        if config_file is None:
            # Default to config file in the same directory as this script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(script_dir, 'calibration_config.yaml')

        super().__init__("01", config_file)
        self.bats_data = self.submodel_config.get("bats_data", False)
    
    def process_data(self) -> dict:
        """Process the usual work and school location data."""
        # Load input data
        logging.info("Loading input data files...")
        taz_data = pd.read_csv(self.config.get('data_sources', 'taz_data'))
        wsloc_results = pd.read_csv(self.submodel_config['input_file'])
        
        # Load distance skim
        dist_skim = pd.read_csv(self.config.get('data_sources', 'dist_skim'), header=0,
                               usecols = ['orig', 'dest', 'DIST'])
        
        # Add Home COUNTY
        logging.info("Merging Home County Data")
        wsloc_results = add_county_info(wsloc_results, taz_data, self.county_lookup,
                                       taz_col='HomeTAZ',
                                       county_col_name='HomeCOUNTY',
                                       county_name_col='HomeCounty_name')
        
        # Add Work and School COUNTY
        logging.info("Merging Work and School County Data")
        wsloc_results = add_county_info(wsloc_results, taz_data, self.county_lookup,
                                       taz_col='WorkLocation',
                                       county_col_name='WorkCOUNTY',
                                       county_name_col='WorkCounty_name')
        
        wsloc_results = add_county_info(wsloc_results, taz_data, self.county_lookup,
                                       taz_col='SchoolLocation',
                                       county_col_name='SchoolCOUNTY',
                                       county_name_col='SchoolCounty_name')
        
        # Attach distances from distance skim
        logging.info("Attaching work distances...")
        work_dist = dist_skim.rename(columns={'orig': 'HomeTAZ', 'dest': 'WorkLocation', 'DIST': 'WorkDist'})
        wsloc_results = wsloc_results.merge(work_dist, on=['HomeTAZ', 'WorkLocation'], how='left')
        
        logging.info("Attaching school distances...")
        school_dist = dist_skim.rename(columns={'orig': 'HomeTAZ', 'dest': 'SchoolLocation', 'DIST': 'SchoolDist'})
        wsloc_results = wsloc_results.merge(school_dist, on=['HomeTAZ', 'SchoolLocation'], how='left')
        
        
        # Save enhanced wsloc_results with distances
        if self.bats_data:
            # Join with PersonData to get weights BEFORE processing
            person_data = pd.read_csv(r"E:\TM1.7 Calibration\BATS\pipeline_mt_20260130\ctramp\PersonData.csv")
            wsloc_results = wsloc_results.merge(person_data[['hh_id', 'person_id', 'person_weight', 'sampleRate']], left_on = ['HHID', 'PersonID'], right_on = ['hh_id', "person_id"])
            wsloc_results.fillna({'person_weight':0}, inplace = True)

            wsloc_with_dist_file = f"{self.target_dir}/BATS_Summaries/MandatoryLocation_with_Distance.csv"
            
            # Process county summary using person weights
            wsloc_county = wsloc_results.groupby(['HomeCounty_name', 'WorkCounty_name'])['person_weight'].sum().reset_index(name='num_pers')
        else:
            wsloc_with_dist_file = f"{self.output_dir}/wsloc_results_with_distances.csv"
            
            # Process county summary using sampleshare
            wsloc_county = wsloc_results.groupby(['HomeCounty_name', 'WorkCounty_name']).size().reset_index(name='num_pers')
            wsloc_county['num_pers'] = wsloc_county['num_pers'] / self.sampleshare
        
        wsloc_county_spread = wsloc_county.pivot(index='HomeCounty_name', columns='WorkCounty_name', values='num_pers')
        wsloc_county_spread = wsloc_county_spread.fillna(0).reset_index()

        wsloc_results.to_csv(wsloc_with_dist_file, index=False)
        logging.info(f"Saved wsloc results with distances to {wsloc_with_dist_file}")

        # Process trip length distributions and averages
        logging.info("Processing trip length distributions...")
        trip_types = ['work', 'univ', 'school']
        trip_tlfd_results = {}
        avg_trip_lengths = []
        
        for trip_type in trip_types:
            # Filter data based on trip type and use attached distances           
            if trip_type == 'work':
                filter_cols = ['HomeCounty_name', 'EmploymentCategory', 'WorkDist']
                if self.bats_data:
                    filter_cols.append('person_weight')
                trip_dists = wsloc_results[wsloc_results['WorkLocation'] > 0][filter_cols].copy()
                trip_dists = trip_dists.rename(columns={'WorkDist': 'DIST'})
            elif trip_type == 'univ':
                filter_cols = ['HomeCounty_name', 'StudentCategory', 'SchoolDist']
                if self.bats_data:
                    filter_cols.append('person_weight')
                trip_dists = wsloc_results[
                    (wsloc_results['SchoolLocation'] > 0) & 
                    (wsloc_results['StudentCategory'] == "College or higher")
                ][filter_cols].copy()
                trip_dists = trip_dists.rename(columns={'SchoolDist': 'DIST'})
            elif trip_type == 'school':
                filter_cols = ['HomeCounty_name', 'StudentCategory', 'SchoolDist']
                if self.bats_data:
                    filter_cols.append('person_weight')
                trip_dists = wsloc_results[
                    (wsloc_results['SchoolLocation'] > 0) & 
                    (wsloc_results['StudentCategory'] == "Grade or high school")
                ][filter_cols].copy()
                trip_dists = trip_dists.rename(columns={'SchoolDist': 'DIST'})
            
            # Calculate trip length frequency distribution
            if self.bats_data:
                trip_tlfd = pd.DataFrame({'distbin': range(1, 52)})
            else:
                trip_tlfd = pd.DataFrame({'distbin': range(1, 151)})
            
            # Process by county
            for county in self.county_lookup.values():
                county_trip_dists = trip_dists[trip_dists['HomeCounty_name'] == county]
                
                if len(county_trip_dists) > 0:
                    if self.bats_data:
                        hist_df = create_histogram_tlfd(county_trip_dists['DIST'], bins = range(52),
                                                       weights=county_trip_dists['person_weight'])
                        # Weighted average
                        weighted_mean = np.average(county_trip_dists['DIST'], 
                                                  weights=county_trip_dists['person_weight'])
                    else:
                        hist_df = create_histogram_tlfd(county_trip_dists['DIST'], 
                                                       sampleshare=self.sampleshare)
                        weighted_mean = county_trip_dists['DIST'].mean()
                    
                    # Remove county prefix for column name
                    col_name = county
                    hist_df = hist_df.rename(columns={'count': col_name})
                    trip_tlfd = trip_tlfd.merge(hist_df, on='distbin', how='left')
                    
                    # Add to average trip lengths
                    avg_trip_lengths.append({
                        'county': col_name,
                        'trip_type': trip_type,
                        'mean_trip_length': weighted_mean
                    })
            
            # Total across all counties
            if len(trip_dists) > 0:
                if self.bats_data:
                    hist_df = create_histogram_tlfd(trip_dists['DIST'], bins = range(52),
                                                   weights=trip_dists['person_weight'])
                    # Weighted average
                    total_weighted_mean = np.average(trip_dists['DIST'], 
                                                    weights=trip_dists['person_weight'])
                else:
                    hist_df = create_histogram_tlfd(trip_dists['DIST'], 
                                                   sampleshare=self.sampleshare)
                    total_weighted_mean = trip_dists['DIST'].mean()
                
                hist_df = hist_df.rename(columns={'count': 'Total'})
                trip_tlfd = trip_tlfd.merge(hist_df, on='distbin', how='left')
                
                avg_trip_lengths.append({
                    'county': 'Total',
                    'trip_type': trip_type,
                    'mean_trip_length': total_weighted_mean
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
        
        # Validate output data
        #         
        return {
            'county_summary': wsloc_county_spread,
            'trip_tlfd_work': trip_tlfd_results.get('work'),
            'trip_tlfd_univ': trip_tlfd_results.get('univ'),
            'trip_tlfd_school': trip_tlfd_results.get('school'),
            'avg_trip_lengths': avg_triplen_spread
        }
    
    def validate_outputs(self, results:dict):
        """Validate outputs before generating the files and updating excel"""
        logging.info("Validating output files")

        # Validate county summary
        if results['county_summary'] is not None:
            validate_dataframe(results['county_summary'], CountySummary)
            logging.info("✓ County Summary Validated")

        # Validate trip length frequency distribution
        expected_rows = 51 if self.bats_data else 150
        for trip_type in ['work', 'univ', 'school']:
            df = results[f'trip_tlfd_{trip_type}']
            if df is not None:
                validate_dataframe(df, TripLengthFrequency, expected_rows)
                logging.info(f"✓ {trip_type.capitalize()} TLFD validated")
        
        # Validate average trip lengths
        if results['avg_trip_lengths'] is not None:
            validate_dataframe(results['avg_trip_lengths'], AverageTripLength, )


    def generate_outputs(self, results: dict):
        """Generate output files and Excel updates."""
        logging.info("Generating output files and Excel updates...")

        if (self.bats_data):
            trip_types = [('work', 2), ('univ', 15), ('school', 28)]
            for trip_type, col in trip_types:
                if results[f'trip_tlfd_{trip_type}'] is not None:
                    tlfd_file = f"{self.target_dir}/BATS_Summaries/{trip_type}TLFD.csv"
                    results[f'trip_tlfd_{trip_type}'].to_csv(tlfd_file, index = False)
                    self.write_dataframe_to_sheet(results[f'trip_tlfd_{trip_type}'], start_row= 4,  start_col=col, sheet_name="CHTS TLFD",
                                                 source_row=2, source_col=col, source_text=f"Source: {tlfd_file}")
                    
                    logging.info(f"Saving trip length frequency distributions for {trip_type} to {tlfd_file}")     
        
            # Average trip lengths
            avg_length_file = f"{self.target_dir}/BATS_Summaries/AvgTripLen.csv"
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


# %%
