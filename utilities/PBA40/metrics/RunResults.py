import argparse
import collections
import operator
import os
import re
import string
import sys
import csv
from collections import OrderedDict, defaultdict
from shutil import copyfile

import pandas as pd     # yay for DataFrames and Series!
import numpy
import math
import xlwings as xl
import xlsxwriter       # for writing workbooks -- formatting is better than openpyxl
from xlsxwriter.utility import xl_range, xl_rowcol_to_cell
pd.set_option('display.precision',10)
pd.set_option('display.width', 500)

USAGE = """


  This script reads "\\\\mainmodel\\MainModelShare\\travel-model-one-master\\utilities\\PBA40\\metrics\\PPAMasterInput.xlsx"
  It also reads transit_crowding.csv. i.e. Prior to running this script, TransitCrowding.py needs to be executed.

  It calculates the project_metrics_dir and produces:
  * project_metrics_dir\BC_ProjectID[_BaseProjectID].xlsx with run results summary
  * all_projects_metrics_dir\BC_ProjectID[_BaseProjectID].csv with a version for rolling up
  * logsum diff maps in \OUTPUT\logsums\logsum_diff.twb

  Run the script from the "M:\Application\Model One\RTP2021\ProjectPerformanceAssessment\Projects" folder, where the baseline runs are saved.
  example: python \\mainmodel\MainModelShare\travel-model-one-master\utilities\PBA40\metrics\RunResults.py 1_Crossings1\2050_TM151_PPA_RT_02_1_Crossings1_03 all_projects_bc_workbooks


"""

class RunResults:
    """
    This represents the run results for a single model run, to be used to calculate
    the benefits/costs results from comparing two runs.
    """

    # Required keys for each project in the BC_config.csv
    REQUIRED_KEYS = [
      'Project ID'  ,  # String identifier for the project
      'Project Name',  # Descriptive name for the project
      'County'      ,  # County where the project is located
      'Project Type',  # Categorization of the project
      'Project Mode',  # Road or transit submode.  Used for Out-of-vehicle Transit Travel Time adjustments
      'Future'      ,  # Future scenario to run the project
      'Compare'                   # one of 'baseline-scenario' or 'scenario-baseline'
      ]


    # Do these ever change?  Should they go into BC_config.csv?
    YEARLY_AUTO_TRIPS_PER_AUTO  = 1583

    ANNUALIZATION               = 300
    WORK_ANNUALIZATION          = 250
    DISCOUNT_RATE               = 0.04

    # per 100000. Crude mortality rate.  For HEAT mortality calcs    ##### AT CHECK THIS
    BAY_AREA_MORTALITY_RATE_2074YRS = 340
    BAY_AREA_MORTALITY_RATE_2064YRS = 232
    WALKING_RELATIVE_RISK = 0.89
    CYCLING_RELATIVE_RISK = 0.90
    WALKING_REF_WEEKLY_MIN = 168
    CYCLING_REF_WEEKLY_MIN = 100

    # logsum cliff effect mitigation    ##### AT CHECK THIS
    CEM_THRESHOLD = 0.1
    CEM_SHALLOW    = 0.05

    COUNTY_NUM_TO_NAME          = {
       1:'San Francisco',
       2:'San Mateo',
       3:'Santa Clara',
       4:'Alameda',
       5:'Contra Costa',
       6:'Solano',
       7:'Napa',
       8:'Sonoma',
       9:'Marin'
    }

    # From 'Plan Bay Area Performance Assessment Report_FINAL.pdf'
    # Model output only captured direct particulate matter emissions; emissions were
    # scaled up to account for particulate emissions from road dust and brake/tire
    # wear
    METRIC_TONS_TO_US_TONS      = 1.10231            # Metric tons to US tons
    PM25_ROADDUST               = 0.018522           # Grams of PM2.5 from road dust per vehicle mile
                                                     # Source: CARB - Section 7.  ARB Miscellaneous Processes Methodologies
                                                     #         Paved Road Dust [Revised and updated, March 2018]
                                                     #         https://www.arb.ca.gov/ei/areasrc/fullpdf/full7-9_2018.pdf
    GRAMS_TO_US_TONS            = 0.00000110231131  # Grams to US tons

    # Already annual -- don't annualize. Default false.
    ALREADY_ANNUAL = {
    ('Other Transportation Benefits','Vehicle Ownership'          ): True,
    ('Other Travel Metrics (for reference only)','Vehicle Ownership (Modeled)'                 ): True,
    ('Other Travel Metrics (for reference only)','Vehicle Ownership (Est. from Auto Trips)'    ): True,
    ('Environmental Benefits','Natural Land (acres)'  ): True,
    ('Health Benefits','Active Individuals (Morbidity)','Total'  ): True,
    ('Health Benefits','Activity: Est Proportion Deaths Averted' ): True,
    ('Health Benefits','Activity: Est Deaths Averted (Mortality)'): True,
    ('Safety Benefits','CRF-based reduction in Collisions'       ): True,
    }

    # Already a diff -- don't diff. Default false.
    ALREADY_DIFF = {
    ('Accessibility Benefits (household-based) (with CEM)','Logsum Hours - Mandatory Tours - Workers & Students'): True,
    ('Accessibility Benefits (household-based) (with CEM)','Logsum Hours - NonMandatory Tours - All people'     ): True,
    ('Accessibility Benefits (household-based) (no CEM)',   'Logsum Hours - Mandatory Tours - Workers & Students'): True,
    ('Accessibility Benefits (household-based) (no CEM)',   'Logsum Hours - NonMandatory Tours - All people'     ): True,
    ('Environmental Benefits','Natural Land (acres)'        ): True,
    ('Safety Benefits','CRF-based reduction in Collisions'  ): True,
    }

    # default is ANNUALIZATION
    ANNUALIZATION_FACTOR = {
    ('Accessibility Benefits (household-based) (with CEM)','Logsum Hours - Mandatory Tours - Workers & Students'): WORK_ANNUALIZATION,
    ('Accessibility Benefits (household-based) (no CEM)','Logsum Hours - Mandatory Tours - Workers & Students'): WORK_ANNUALIZATION,
    }



    def __init__(self, rundir, bc_config='BC_config.csv', overwrite_config=None):
        """
    Parameters
    ----------
    rundir : string
        The directory containing the raw output for the model run.
    overwrite_config : dict
        Pass overwrite config if this is a base scenario and we should use the
        project's ovtt adjustment mode.

    Read configuration and input data.
    """
        self.ppa_master_input = "\\\\mainmodel\\MainModelShare\\travel-model-one-master\\utilities\\PBA40\\metrics\\PPAMasterInput.xlsx"

        # read the configs
        self.rundir = os.path.join(os.path.abspath(rundir), 'OUTPUT', 'metrics')
        # if this is a baseline run, then read from configs_base sheet of master input file
        # else this is a project run, then read from configs_projects sheet of master input file
        #if 'CaltrainMod_00' not in rundir:  #for RTFF
        if len(rundir) > 22:
            configs_df = pd.read_excel(self.ppa_master_input, sheet_name='configs_projects', header=0)
            configs_df.insert(0,'Folder','')
            configs_df['Folder'] =  configs_df[['Foldername - Project', 'Foldername - Future']].apply(lambda x: '\\'.join(x), axis=1)
            configs_df.drop(['Foldername - Project', 'Foldername - Future'], axis=1)
        else:
            configs_df = pd.read_excel(self.ppa_master_input, sheet_name='configs_base', header=0)
        configs_df = configs_df.T
        configs_df.columns = configs_df.iloc[0]
        configs_df = configs_df[1:]
        self.config = configs_df[[rundir]].iloc[:,0]
        self.config['Project Run Dir'] = self.rundir

        # read the Benefit Valuations depending on future
        # See RAWG Dec 2018'Plan Bay Area Performance Assessment Report_FINAL.pdf'
        # Table 9: Benefit Valuations
        # Units in 2017 dollars
        # this sets it into the format {('cat1','cat2','cat3'):[val0,val1,val2,val3]} where vals are base, CAG, RTFF, BTTF

        valuations_df = pd.read_excel(self.ppa_master_input, sheet_name='valuations', header=0)
        self.BENEFIT_VALUATION = valuations_df.set_index(['Benefit Category 1','Benefit Category 2','Benefit Category 3']).T.to_dict('list')

        # dict with 3-tuple keys and some have a 3rd val of "NAN"
        old_keys = self.BENEFIT_VALUATION.keys()

        for dict_key in old_keys:
            # this one is bad
            try:
                if math.isnan(float(dict_key[2])):
                    self.BENEFIT_VALUATION[(dict_key[0],dict_key[1])] = self.BENEFIT_VALUATION.get(dict_key)
                    del self.BENEFIT_VALUATION[dict_key]
            except:
                None

        if self.config.loc['Future'] in ['CAG']:
            for k, v in self.BENEFIT_VALUATION.iteritems():
                del v[3], v[2], v[0]
        elif self.config.loc['Future'] in ['RTFF']:
            for k, v in self.BENEFIT_VALUATION.iteritems():
                del v[3], v[0], v[0]
        elif self.config.loc['Future'] in ['BTTF']:
            for k, v in self.BENEFIT_VALUATION.iteritems():
                del v[0], v[0], v[0]


        self.base_results = None

        # Make sure required values are in the configuration
        print("Reading result csvs from '%s'" % self.rundir)
        try:
            for key in RunResults.REQUIRED_KEYS:
                config_key  = '%s' % key
                print("  %25s '%s'" % (config_key, self.config.loc[config_key]))

        except KeyError as e:
            print("Config missing required variable: %s" %str(e))
            sys.exit(2)

        self.is_base_dir = False
        if overwrite_config:
            self.is_base_dir = True
            for key in overwrite_config.keys(): self.config[key] = overwrite_config[key]
            print ("OVERWRITE_CONFIG FOR BASE_DIR: ")
            print self.config

        elif 'base_dir' not in self.config.keys():
            self.is_base_dir = True

        print("")
        # read the csvs
        self.auto_times = \
            pd.read_table(os.path.join(self.rundir, "auto_times.csv"),
                          sep=",", index_col=[0,1])
        # print self.auto_times

        self.autos_owned = \
            pd.read_table(os.path.join(self.rundir, "autos_owned.csv"),
                          sep=",")
        self.autos_owned['total autos'] = self.autos_owned['households']*self.autos_owned['autos']
        self.autos_owned.set_index(['incQ','autos'],inplace=True)
        # print self.autos_owned

        self.parking_costs = \
            pd.read_table(os.path.join(self.rundir, "parking_costs.csv"),
                          sep=",")
        # print self.parking_costs.head()

        self.vmt_vht_metrics = \
            pd.read_table(os.path.join(self.rundir, "vmt_vht_metrics.csv"),
                          sep=",", index_col=[0,1])
        # print self.vmt_vht_metrics

        self.nonmot_times = \
            pd.read_table(os.path.join(self.rundir, "nonmot_times.csv"),
                                       sep=",", index_col=[0,1,2])
        # print self.nonmot_times

        self.transit_boards_miles = \
            pd.read_table(os.path.join(self.rundir, "transit_boards_miles.csv"),
                          sep=",", index_col=0)
        # print self.transit_boards_miles

        self.transit_times_by_acc_mode_egr = \
            pd.read_table(os.path.join(self.rundir, "transit_times_by_acc_mode_egr.csv"),
                          sep=",", index_col=[0,1,2,3])
        # print self.transit_times_by_acc_mode_egr

        self.transit_times_by_mode_income = \
            pd.read_table(os.path.join(self.rundir, "transit_times_by_mode_income.csv"),
                          sep=",", index_col=[0,1])
        # print self.transit_times_by_mode_income

        self.unique_active_travelers = pd.Series.from_csv(os.path.join(self.rundir, "unique_active_travelers.csv"))
        # print self.unique_active_travelers

        self.crowding_df = pd.read_csv(os.path.join(self.rundir, "transit_crowding.csv"))
        self.crowding_complete_df = pd.read_csv(os.path.join(self.rundir, "transit_crowding_complete.csv"))

        #####################################

        # Reading from master excel input file
        if 'base_dir' in self.config.keys():

            # Project costs
            df_costs = pd.read_excel(self.ppa_master_input, sheet_name='project_costs', header=0)
            df_costs = df_costs[df_costs['project_id'] == int(self.config.loc['Project ID'].split('_')[0])]
            self.proj_costs = df_costs.to_dict('records', into=OrderedDict)[0]

            # asset life
            df_asset_life =  pd.read_excel(self.ppa_master_input, sheet_name='asset_life', header=0)
            self.asset_life = df_asset_life.set_index(['asset_class']).T.to_dict('records', into=OrderedDict)[0]

            # CRF-related collisions
            df_collisions_SWITRS = pd.read_excel(self.ppa_master_input, sheet_name='collisions_switrs', header=0)
            new_header = df_collisions_SWITRS.iloc[0] #grab the first row for the header
            df_collisions_SWITRS = df_collisions_SWITRS[1:] #take the data less the header row
            df_collisions_SWITRS.columns = new_header

            df_collisions_SWITRS2 = df_collisions_SWITRS[df_collisions_SWITRS['project_id'] == int(self.config.loc['Project ID'].split('_')[0])]
            if df_collisions_SWITRS2.shape[0] == 0:
                df_collisions_SWITRS2 = df_collisions_SWITRS[df_collisions_SWITRS['project_id'] == 0]
            self.collisions_switrs = df_collisions_SWITRS2.to_dict('records', into=OrderedDict)[0]


            # Natural Land
            df_natural_land = pd.read_excel(self.ppa_master_input, sheet_name='natural_land', header=0)
            df_natural_land2 = df_natural_land[df_natural_land['project_id'] == int(self.config.loc['Project ID'].split('_')[0])]
            if df_natural_land2.shape[0] == 0:
                df_natural_land2 = df_natural_land[df_natural_land['project_id'] == 0]
            self.natural_land = df_natural_land2.to_dict('records', into=OrderedDict)[0]

            # Guiding Principles
            df_gp = pd.read_excel(self.ppa_master_input, sheet_name='guiding_principles', header=0)
            df_gp2 = df_gp[df_gp['project_id'] == int(self.config.loc['Project ID'].split('_')[0])]
            if df_gp2.shape[0] == 0:
                df_gp2 = df_gp[df_gp['project_id'] == 0]
            df_gp2 = df_gp2.drop(['project_id'], axis=1)
            self.gp = df_gp2.to_dict('records', into=OrderedDict)[0]



        # read roadway network for truck costs
        roadway_read    = False

        # on M
        roadway_netfile = os.path.abspath(os.path.join(self.rundir, "..", "avgload5period_vehclasses.csv"))
        if os.path.exists(roadway_netfile):
            self.roadways_df = pd.read_table(roadway_netfile, sep=",")
            #print "Read roadways from %s" % roadway_netfile
            roadway_read = True

        # on model machine for reading baseline
        if not roadway_read:
            roadway_netfile = os.path.abspath(os.path.join(self.rundir, "..", "extractor", "avgload5period_vehclasses.csv"))
            if os.path.exists(roadway_netfile):
                self.roadways_df = pd.read_table(roadway_netfile, sep=",")
                print "Read roadways from %s" % roadway_netfile
                roadway_read = True

        # on model machine for reading non-baseline
        if not roadway_read:
            if 'ITER' not in os.environ:
                print "Could not find roadway network in %s" % roadway_netfile
                print "So looking in hwy/iterX but ITER isn't in the environment."
                sys.exit(2)

            roadway_netfile = os.path.abspath(os.path.join(self.rundir, "..", "hwy", "iter%s" % os.environ['ITER'], "avgload5period_vehclasses.csv"))
            self.roadways_df = pd.read_table(roadway_netfile, sep=",")
            print "Read roadways from %s" % roadway_netfile
            roadway_read = True

        # aggregate truck volumes
        self.roadways_df['small truck volume'] = self.roadways_df.volEA_sm + self.roadways_df.volEA_smt + \
                                                 self.roadways_df.volAM_sm + self.roadways_df.volAM_smt + \
                                                 self.roadways_df.volMD_sm + self.roadways_df.volMD_smt + \
                                                 self.roadways_df.volPM_sm + self.roadways_df.volPM_smt + \
                                                 self.roadways_df.volEV_sm + self.roadways_df.volEV_smt
        self.roadways_df['large truck volume'] = self.roadways_df.volEA_hv + self.roadways_df.volEA_hvt + \
                                                 self.roadways_df.volAM_hv + self.roadways_df.volAM_hvt + \
                                                 self.roadways_df.volMD_hv + self.roadways_df.volMD_hvt + \
                                                 self.roadways_df.volPM_hv + self.roadways_df.volPM_hvt + \
                                                 self.roadways_df.volEV_hv + self.roadways_df.volEV_hvt

        for filename in ['mandatoryAccessibilities', 'nonMandatoryAccessibilities']:
            accessibilities = \
                pd.read_table(os.path.join(self.rundir, "..", "logsums", "%s.csv" % filename),
                              sep=",")
            accessibilities.drop('destChoiceAlt', axis=1, inplace=True)
            accessibilities.set_index(['taz','subzone'], inplace=True)
            # put 'lowInc_0_autos' etc are in a column not column headers
            accessibilities = pd.DataFrame(accessibilities.stack())
            accessibilities.reset_index(inplace=True)
            # split the income/auto sufficiency column into three columns
            accessibilities['incQ_label']     = accessibilities['level_2'].str.split('_',n=1).str.get(0)
            accessibilities['autoSuff_label'] = accessibilities['level_2'].str.split('_',n=1).str.get(1)
            accessibilities['autoSuff_label'] = accessibilities['autoSuff_label'].str.rsplit('_',n=1).str.get(0)
            accessibilities['hasAV']          = accessibilities.apply(lambda row: 0 if "noAV" in row['level_2'] else 1, axis=1)
            # remove the now extraneous 'level_2'
            accessibilities.drop('level_2', axis=1, inplace=True)

            if self.is_base_dir: col_prefix = 'base'
            else:                col_prefix = 'scen'

            accessibilities.rename(columns={0:'%s_dclogsum' % col_prefix,
                                                 'subzone':'walk_subzone'},
                                        inplace=True)

            if filename == 'mandatoryAccessibilities':
                self.mandatoryAccessibilities = accessibilities
            elif filename == 'nonMandatoryAccessibilities':
                self.nonmandatoryAccessibilities = accessibilities

        self.accessibilityMarkets = \
            pd.read_table(os.path.join(self.rundir, "..", "core_summaries", "AccessibilityMarkets.csv"),
                          sep=",")

        self.accessibilityMarkets.rename(columns={'num_persons':'%s_num_persons' % col_prefix,
                                                  'num_workers':'%s_num_workers' % col_prefix,
                                                  'num_workers_students':'%s_num_workers_students' % col_prefix},
                                         inplace=True)


    def createBaseRunResults(self):
        """
        Create instance of RunResults representing the base, if applicable.
        """
        try:
            self.base_dir     = self.config.loc['base_dir']
            print self.base_dir
        except:
            # this is ok -- no base_dir specified
            self.base_dir     = None

        if self.base_dir:
            # these are not ok - let exceptions raise
            print("")
            print("BASE:")
            #self.base_dir = os.path.realpath(self.base_dir)

            # pass the project mode for overwrite to base
            base_overwrite_config = {}
            base_overwrite_config['Project Mode'] = self.config.loc['Project Mode']

            print self.base_dir
            #print base_overwrite_config
            self.base_results = RunResults(rundir = self.base_dir,
                                           overwrite_config=base_overwrite_config)

    def updateDailyMetrics(self):
        """
        Updates calculated metrics that depend on base results.
        """
        # apply incease in Auto hours to base truck hours
        if not self.base_results: return

        cat1            = 'Travel Time Stats (for reference only)'
        cat2            = 'Auto Hours (Person Hours)'
        auto_vht        = self.daily_results[cat1,cat2,'SOV (PHT)'  ] + \
                          self.daily_results[cat1,cat2,'HOV2 (PHT)' ] + \
                          self.daily_results[cat1,cat2,'HOV3+ (PHT)']
        base_auto_vht   = self.base_results.daily_results[cat1,cat2,'SOV (PHT)'  ] + \
                          self.base_results.daily_results[cat1,cat2,'HOV2 (PHT)' ] + \
                          self.base_results.daily_results[cat1,cat2,'HOV3+ (PHT)']
        cat2            = 'Truck Hours'
        base_truck_vht  = self.base_results.daily_results[cat1,cat2,'Truck (Computed VHT)']

        pct_change_vht  = (auto_vht-base_auto_vht)/base_auto_vht
        self.daily_results[                cat1,           cat2,       'Truck (Computed VHT)'] = (1.0+pct_change_vht)*base_truck_vht
        self.daily_results['Accessibility Benefits (other)','Non-Household','Time - Truck (Computed VHT)'] = (1.0+pct_change_vht)*base_truck_vht

        cat2            = 'Non-Recurring Freeway Delay (Hours)'
        auto_nrfd       = self.daily_results[cat1,cat2,'Auto (Person Hours)']
        base_auto_nrfd  = self.base_results.daily_results[cat1,cat2,'Auto (Person Hours)']
        base_truck_nrfd = self.base_results.daily_results[cat1,cat2,'Truck (Computed VH)']

        pct_change_nrfd = (auto_nrfd-base_auto_nrfd)/base_auto_nrfd
        self.daily_results[                cat1,cat2,'Truck (Computed VH)'] = (1.0+pct_change_nrfd)*base_truck_nrfd
        self.daily_results['Other Transportation Benefits','Travel Time Reliability (Non-Recurring Freeway Delay) (Hours)','Truck (Computed VH)'] = (1.0+pct_change_nrfd)*base_truck_nrfd


        ################

        cat1            = 'Other Travel Metrics (for reference only)'

        cat2            = 'VMT by class'
        auto_vmt        = self.daily_results[cat1,cat2,'Auto non-AV'] + self.daily_results[(cat1,cat2,'Auto AV' )]
        base_auto_vmt   = self.base_results.daily_results[cat1,cat2,'Auto non-AV'] + self.base_results.daily_results[cat1,cat2,'Auto AV']
        base_truck_vmt  = self.base_results.daily_results[cat1,cat2,'Truck - Computed']

        pct_change_vmt  = (auto_vmt-base_auto_vmt)/base_auto_vmt
        self.daily_results[cat1,cat2,'Truck - Computed'] = (1.0+pct_change_vmt)*base_truck_vmt

        vmt_trucks = self.quick_summary['VMT -- trucks']
        vmt_total = self.quick_summary['VMT -- all vehicles']
        self.quick_summary['VMT -- trucks'] = (1.0+pct_change_vmt)*base_truck_vmt
        self.quick_summary['VMT -- all vehicles'] = vmt_total - vmt_trucks + ((1.0+pct_change_vmt)*base_truck_vmt)

        ################

        # this is dependent on VMT so it also needs updating
        cat1            = 'Health Benefits'
        cat2            = 'PM2.5 (tons)'
        self.daily_results[cat1,cat2,'PM2.5 Road Dust'] = \
             (self.daily_results['Other Travel Metrics (for reference only)','VMT by class','Auto non-AV'] + \
              self.daily_results['Other Travel Metrics (for reference only)','VMT by class','Auto AV'] +\
              self.daily_results['Other Travel Metrics (for reference only)','VMT by class','Truck - Computed']) * \
                    RunResults.PM25_ROADDUST*RunResults.GRAMS_TO_US_TONS

        ################

        cat1            = 'Other Travel Metrics (for reference only)'
        cat2            = 'Operating Costs ($2000)'
        # override the truck vmt with base truck vmt, with pct change auto vmt applied
        self.roadways_df = pd.merge(left=self.roadways_df,
                                    right=self.base_results.roadways_df[['a','b','small truck volume','large truck volume']],
                                    how='left', on=['a','b'], suffixes=(' scenario',' baseline'))
        self.roadways_df['small truck volume'] = self.roadways_df['small truck volume baseline']*(1.0+pct_change_vmt)
        self.roadways_df['large truck volume'] = self.roadways_df['large truck volume baseline']*(1.0+pct_change_vmt)
        # calculate the new truck cost with these assumed truck VMTs
        self.roadways_df['total truck cost']   = (self.roadways_df['small truck volume']*self.roadways_df['smtropc']*self.roadways_df['distance']*0.01) + \
                                                 (self.roadways_df['large truck volume']*self.roadways_df['lrtropc']*self.roadways_df['distance']*0.01)

        self.daily_results[                cat1,           cat2,       'Truck - Computed'] = self.roadways_df['total truck cost'].sum()
        self.daily_results['Accessibility Benefits (other)','Non-Household','Cost - Truck ($2000) - Computed'] = self.roadways_df['total truck cost'].sum()

        cat1            = 'Health Benefits'
        cat2            = 'Noise'
        self.daily_results[cat1,cat2,'Truck VMT - Computed'] = (1.0+pct_change_vmt)*base_truck_vmt


    def parseNumList(self, numlist_str):
        """
        Parses a number list of the format 1,4,6,10-14,23 into a list of numbers.

        Used for Zero Logsum TAZs parsing
        """
        # Parse the taz list.
        taz_list_strs = numlist_str.split(",")
        # these should be either 123 or 1-123
        taz_list = []
        for taz_list_str in taz_list_strs:
            taz_list_regex = re.compile(r"(\d+)(-(\d+))?")
            match_obj = re.match(taz_list_regex, taz_list_str)
            if match_obj.group(3) == None:
                taz_list.append(int(match_obj.group(1)))
            else:
                taz = int(match_obj.group(1))
                while taz <= int(match_obj.group(3)):
                    taz_list.append(taz)
                    taz += 1
        return taz_list

    def calculateDailyMetrics(self):
        """
        Calculates the daily output metrics which will actually get used for the benefits/cost
        analysis.

        Sets these into self.daily_results, a pandas.Series with a 3-level MultiIndex: category1,
          category2, variable_name.

        Creates self.quick_summary results as well, a panda.Series with a simple string index.
        """

        # we really want these by class -- ignore time periods and income levels
        vmt_byclass     = self.vmt_vht_metrics.sum(level='vehicle class') # vehicles, not people
        transit_byclass = self.transit_times_by_acc_mode_egr.loc['all'].sum(level='Mode')
        transit_byaceg  = self.transit_times_by_acc_mode_egr.loc['all'].sum(level=['Access','Egress'])
        nonmot_byclass  = self.nonmot_times.loc['all'].sum(level='Mode')  # person trips
        auto_byclass    = self.auto_times.sum(level='Mode')               # person trips



        daily_results   = collections.OrderedDict()
        quick_summary   = {}
        ######################################################################################
        if self.base_results:
            zero_neg_taz_list = []
            zero_taz_list     = []
            if ("Zero Logsum TAZs" in self.config) or ("Zero Negative Logsum TAZs" in self.config):
                # Require a readme about it
                readme_file = os.path.join(self.rundir, "Zero Out Logsum Diff README.txt")
                if not os.path.exists(readme_file):
                    print "Readme file [%s] doesn't exist -- this is required to use this configuration option." % readme_file
                    sys.exit(2)

                if os.path.getsize(readme_file) < 200:
                    print "Readme file [%s] is pretty short... It should have more detail about why you're doing this." % readme_file
                    sys.exit(2)

                if "Zero Negative Logsum TAZs" in self.config:
                    zero_neg_taz_list = self.parseNumList(self.config["Zero Negative Logsum TAZs"])
                    print "Zeroing out negative diffs for tazs %s" % str(zero_neg_taz_list)

                if "Zero Logsum TAZs" in self.config:
                    zero_taz_list = self.parseNumList(self.config["Zero Logsum TAZs"])
                    print "Zeroing out diffs for tazs %s" % str(zero_taz_list)

            # Take the difference and convert utils to minutes (k_ivt = 0.0134 k_mc_ls = 1.0 in access calcs);
            # TODO: is k_mc_ls = 1.0?  DestinationChoice.cls has different values
            self.mandatoryAccessibilities = pd.merge(self.mandatoryAccessibilities,
                                                     self.base_results.mandatoryAccessibilities,
                                                    how='left')
            self.mandatoryAccessibilities['diff_dclogsum'] = \
                self.mandatoryAccessibilities.scen_dclogsum - self.mandatoryAccessibilities.base_dclogsum

            # zero out negative diffs if directed
            if len(zero_neg_taz_list) > 0:
                self.mandatoryAccessibilities.loc[(self.mandatoryAccessibilities.taz.isin(zero_neg_taz_list)) & (self.mandatoryAccessibilities.diff_dclogsum<0), 'diff_dclogsum'] = 0.0

            # zero out diffs if directed
            if len(zero_taz_list) > 0:
                self.mandatoryAccessibilities.loc[self.mandatoryAccessibilities.taz.isin(zero_taz_list), 'diff_dclogsum'] = 0.0

            self.mandatoryAccessibilities['logsum_diff_minutes'] = self.mandatoryAccessibilities.diff_dclogsum / 0.0134


            # Cliff Effect Mitigation
            mand_ldm_max = self.mandatoryAccessibilities.logsum_diff_minutes.abs().max()
            if mand_ldm_max < 0.00001:
                self.mandatoryAccessibilities['ldm_ratio'] = 1.0
                self.mandatoryAccessibilities['ldm_mult' ] = 1.0
            else:
                self.mandatoryAccessibilities['ldm_ratio'] = self.mandatoryAccessibilities.logsum_diff_minutes.abs()/mand_ldm_max    # how big is the magnitude compared to max magnitude?
                self.mandatoryAccessibilities['ldm_mult' ] = 1.0/(1.0+numpy.exp(-(self.mandatoryAccessibilities.ldm_ratio-RunResults.CEM_THRESHOLD)/RunResults.CEM_SHALLOW))
            self.mandatoryAccessibilities['ldm_cem']   = self.mandatoryAccessibilities.logsum_diff_minutes*self.mandatoryAccessibilities.ldm_mult

            # print out the mandatory logsum diff, with cem, to a csv file
            mandatory_logsums_filename = os.path.join(os.getcwd(), sys.argv[1], 'OUTPUT', 'logsums', "logsum_diff_mandatory_cem.csv")
            self.mandatoryAccessibilities.to_csv(mandatory_logsums_filename)
            print("Wrote mandatory logsums diff into "+mandatory_logsums_filename)

            # copy Tableau template into the project folder for mapping
            tableau_template="\\\\mainmodel\\MainModelShare\\travel-model-one-master\\utilities\\PBA40\\metrics\\logsum_diff.twb"
            copyfile(tableau_template, os.path.join(os.getcwd(), sys.argv[1], 'OUTPUT', 'logsums', 'logsum_diff.twb'))

            # This too
            self.nonmandatoryAccessibilities = pd.merge(self.nonmandatoryAccessibilities,
                                                        self.base_results.nonmandatoryAccessibilities,
                                                        how='left')
            self.nonmandatoryAccessibilities['diff_dclogsum'] = \
                self.nonmandatoryAccessibilities.scen_dclogsum - self.nonmandatoryAccessibilities.base_dclogsum

            # zero out negative diffs if directed
            if len(zero_neg_taz_list) > 0:
                self.nonmandatoryAccessibilities.loc[(self.nonmandatoryAccessibilities.taz.isin(zero_neg_taz_list)) & (self.nonmandatoryAccessibilities.diff_dclogsum<0), 'diff_dclogsum'] = 0.0

            # zero out diffs if directed
            if len(zero_taz_list) > 0:
                self.nonmandatoryAccessibilities.loc[self.nonmandatoryAccessibilities.taz.isin(zero_taz_list), 'diff_dclogsum'] = 0.0

            self.nonmandatoryAccessibilities['logsum_diff_minutes'] = self.nonmandatoryAccessibilities.diff_dclogsum / 0.0175

            # Cliff Effect Mitigation
            nonmm_ldm_max = self.nonmandatoryAccessibilities.logsum_diff_minutes.abs().max()
            self.nonmandatoryAccessibilities['ldm_ratio'] = self.nonmandatoryAccessibilities.logsum_diff_minutes.abs()/nonmm_ldm_max    # how big is the magnitude compared to max magnitude?
            self.nonmandatoryAccessibilities['ldm_mult' ] = 1.0/(1.0+numpy.exp(-(self.nonmandatoryAccessibilities.ldm_ratio-RunResults.CEM_THRESHOLD)/RunResults.CEM_SHALLOW))
            self.nonmandatoryAccessibilities['ldm_cem']   = self.nonmandatoryAccessibilities.logsum_diff_minutes*self.nonmandatoryAccessibilities.ldm_mult

            # print out the nonmandatory logsum diff, with cem, to a csv file
            nonmandatory_logsums_filename = os.path.join(os.getcwd(), sys.argv[1], 'OUTPUT', 'logsums', "logsum_diff_nonmandatory_cem.csv")
            self.nonmandatoryAccessibilities.to_csv(nonmandatory_logsums_filename)
            print("Wrote non-mandatory logsums diff into "+nonmandatory_logsums_filename)

            self.accessibilityMarkets = pd.merge(self.accessibilityMarkets,
                                                 self.base_results.accessibilityMarkets,
                                                 how='left')

            self.mandatoryAccess = pd.merge(self.mandatoryAccessibilities,
                                            self.accessibilityMarkets,
                                            how='left')

            self.mandatoryAccess.fillna(0, inplace=True)

            self.nonmandatoryAccess = pd.merge(self.nonmandatoryAccessibilities,
                                               self.accessibilityMarkets,
                                               how='left')
            self.nonmandatoryAccess.fillna(0, inplace=True)

            # Cliff Effect Mitigated - rule of one-half
            cat1         = 'Accessibility Benefits (household-based) (with CEM)'
            cat2         = 'Logsum Hours - Mandatory Tours - Workers & Students'
            self.mandatoryAccess['CS diff work/school'] = \
                (0.5*self.mandatoryAccess.base_num_workers_students + 0.5*self.mandatoryAccess.scen_num_workers_students) *self.mandatoryAccess.ldm_cem
            for inclabel in ['lowInc','medInc','highInc','veryHighInc']:
                daily_results[(cat1,cat2,inclabel)] = self.mandatoryAccess.loc[self.mandatoryAccess.incQ_label==inclabel, 'CS diff work/school'].sum()/60.0;

            cat2         = 'Logsum Hours - NonMandatory Tours - All people'
            self.nonmandatoryAccess['CS diff all'] = \
                (0.5*self.nonmandatoryAccess.base_num_persons + 0.5*self.nonmandatoryAccess.scen_num_persons)*self.nonmandatoryAccess.ldm_cem
            for inclabel in ['lowInc','medInc','highInc','veryHighInc']:
                daily_results[(cat1,cat2,inclabel)] = self.nonmandatoryAccess.loc[self.mandatoryAccess.incQ_label==inclabel, 'CS diff all'].sum()/60.0;

            # print out changes in consumer surplus for mandatory tours, with cem, to csv files
            mandatory_cs_filename = os.path.join(os.getcwd(), sys.argv[1], 'OUTPUT', 'logsums', "cs_mandatory_CEM.csv")
            nonmandatory_cs_filename = os.path.join(os.getcwd(), sys.argv[1], 'OUTPUT', 'logsums', "cs_nonmandatory_CEM.csv")
            self.mandatoryAccess.to_csv(mandatory_cs_filename)
            self.nonmandatoryAccess.to_csv(nonmandatory_cs_filename)

            # No Cliff Effect Mitigation - rule of one-half
            cat1         = 'Accessibility Benefits (household-based) (no CEM)'
            cat2         = 'Logsum Hours - Mandatory Tours - Workers & Students'
            self.mandatoryAccess['CS diff work/school'] = \
                (0.5*self.mandatoryAccess.base_num_workers_students + 0.5*self.mandatoryAccess.scen_num_workers_students) *self.mandatoryAccess.logsum_diff_minutes
            for inclabel in ['lowInc','medInc','highInc','veryHighInc']:
                daily_results[(cat1,cat2,inclabel)] = self.mandatoryAccess.loc[self.mandatoryAccess.incQ_label==inclabel, 'CS diff work/school'].sum()/60.0;


            cat2         = 'Logsum Hours - NonMandatory Tours - All people'
            self.nonmandatoryAccess['CS diff all'] = \
                (0.5*self.nonmandatoryAccess.base_num_persons + 0.5*self.nonmandatoryAccess.scen_num_persons)*self.nonmandatoryAccess.logsum_diff_minutes
            for inclabel in ['lowInc','medInc','highInc','veryHighInc']:
                daily_results[(cat1,cat2,inclabel)] = self.nonmandatoryAccess.loc[self.mandatoryAccess.incQ_label==inclabel, 'CS diff all'].sum()/60.0;

            # print out changes in consumer surplus for mandatory tours, with no cem, to csv files
            mandatory_cs_filename = os.path.join(os.getcwd(), sys.argv[1], 'OUTPUT', 'logsums', "cs_mandatory_noCEM.csv")
            nonmandatory_cs_filename = os.path.join(os.getcwd(), sys.argv[1], 'OUTPUT', 'logsums', "cs_nonmandatory_noCEM.csv")
            self.mandatoryAccess.to_csv(mandatory_cs_filename)
            self.nonmandatoryAccess.to_csv(nonmandatory_cs_filename)

        ##########################################################################################

        cat1 = "Accessibility Benefits (other)"

        cat2 = 'Non-Household'

        daily_results[(cat1,cat2,'Time - Auto (PHT) - IX/EX' )] = \
            auto_byclass.loc[['da_ix','datoll_ix','sr2_ix','sr2toll_ix','sr3_ix','sr3toll_ix'],'Person Minutes'].sum()/60.0
        daily_results[(cat1,cat2,'Time - Auto (PHT) - AirPax' )] = \
            auto_byclass.loc[['da_air','datoll_air','sr2_air','sr2toll_air','sr3_air','sr3toll_air'],'Person Minutes'].sum()/60.0
        daily_results[(cat1,cat2,'Time - Truck (Computed VHT)')] = vmt_byclass.loc[['sm','smt','hv','hvt'],'VHT'].sum()

        daily_results[(cat1,cat2,'Cost - Auto ($2000) - IX/EX' )] = \
            0.01*auto_byclass.loc[['da_ix','datoll_ix','sr2_ix','sr2toll_ix','sr3_ix','sr3toll_ix'],'Total Cost'].sum()
        daily_results[(cat1,cat2,'Cost - Auto ($2000) - AirPax' )] = \
            0.01*auto_byclass.loc[['da_air','datoll_air','sr2_air','sr2toll_air','sr3_air','sr3toll_air'],'Total Cost'].sum()
        # get this from the roadway network.
        # smtropc,lrtropc are total opcosts for trucks, in 2000 cents per mile
        self.roadways_df['total truck cost'] = (self.roadways_df['small truck volume']*self.roadways_df['smtropc']*self.roadways_df['distance']*0.01) + \
                                               (self.roadways_df['large truck volume']*self.roadways_df['lrtropc']*self.roadways_df['distance']*0.01)
        daily_results[(cat1,cat2,'Cost - Truck ($2000) - Computed')] = self.roadways_df['total truck cost'].sum()



        cat2 = "Adding Back Societal Transfers"
        self.transit_times_by_mode_income["Total Cost"] = self.transit_times_by_mode_income["Daily Trips"]*self.transit_times_by_mode_income["Avg Cost"]
        daily_results[(cat1,cat2,"Transit Fares ($2000)")] = self.transit_times_by_mode_income["Total Cost"].sum()
        daily_results[(cat1,cat2,"Auto Households - Bridge Tolls ($2000)" )] = \
                                                        0.01*auto_byclass.loc[['da','datoll','da_av_toll', 'da_av_notoll',\
                                                                               'sr2','sr2toll','s2_av_toll', 's2_av_notoll',\
                                                                                'sr3','sr3toll','s3_av_toll', 's3_av_notoll',\
                                                                                'taxi', 'tnc_shared', 'tnc_single', 'zpv_tnc'],'Bridge Tolls'].sum()
        daily_results[(cat1,cat2,"Auto Households - Value Tolls ($2000)"  )] = \
                                                        0.01*auto_byclass.loc[['da','datoll','da_av_toll', 'da_av_notoll',\
                                                                               'sr2','sr2toll','s2_av_toll', 's2_av_notoll',\
                                                                                'sr3','sr3toll','s3_av_toll', 's3_av_notoll',\
                                                                                'taxi', 'tnc_shared', 'tnc_single', 'zpv_tnc'],'Value Tolls'].sum()


        ######################################################################################

        cat1 = "Other Transportation Benefits"

        # These are dupes from below but they're not in logsums
        cat2            = 'Travel Time Reliability (Non-Recurring Freeway Delay) (Hours)'
        daily_results[(cat1,cat2,'Auto (Person Hours)')] = \
            vmt_byclass.loc[['da','dat','daav'],'Non-Recurring Freeway Delay'].sum()   +\
            vmt_byclass.loc[['s2','s2t','s2av'],'Non-Recurring Freeway Delay'].sum()*2 +\
            vmt_byclass.loc[['s3','s3t','s3av'],'Non-Recurring Freeway Delay'].sum()*3.5
        daily_results[(cat1,cat2,'Truck (Computed VH)')] = \
            vmt_byclass.loc[['sm','smt','hv','hvt'],'Non-Recurring Freeway Delay'].sum()


        cat2            = 'Transit Crowding (Crowding Penalty Hours)'
        # crowding penalty = effective ivtt with crowding multiplier minus actual ivtt
        daily_results[(cat1,cat2,'BART (incl eBART)')] = self.crowding_df.loc[self.crowding_df['SYSTEM'] == "BART", 'effective_ivtt_metrolinx_max2pt5'].sum() \
                                          - self.crowding_df.loc[self.crowding_df['SYSTEM'] == "BART", 'ivtt_hours'].sum() \
                                          + self.crowding_df.loc[self.crowding_df['SYSTEM'] == "EBART", 'effective_ivtt_metrolinx_max2pt5'].sum() \
                                          - self.crowding_df.loc[self.crowding_df['SYSTEM'] == "EBART", 'ivtt_hours'].sum()

        daily_results[(cat1,cat2,'Caltrain')] = self.crowding_df.loc[self.crowding_df['SYSTEM'] == "Caltrain", 'effective_ivtt_metrolinx_max2pt5'].sum() \
                                             -  self.crowding_df.loc[self.crowding_df['SYSTEM'] == "Caltrain", 'ivtt_hours'].sum()

        daily_results[(cat1,cat2,'SF Muni')] = self.crowding_df.loc[self.crowding_df['SYSTEM'] == "SF MUNI", 'effective_ivtt_metrolinx_max2pt5'].sum() \
                                            -  self.crowding_df.loc[self.crowding_df['SYSTEM'] == "SF MUNI", 'ivtt_hours'].sum() \
                                            +  self.crowding_df.loc[self.crowding_df['SYSTEM'] == "SF Muni Cable Car", 'effective_ivtt_metrolinx_max2pt5'].sum() \
                                            -  self.crowding_df.loc[self.crowding_df['SYSTEM'] == "SF Muni Cable Car", 'ivtt_hours'].sum()  \
                                            +  self.crowding_df.loc[self.crowding_df['SYSTEM'] == "SF Muni Local", 'effective_ivtt_metrolinx_max2pt5'].sum() \
                                            -  self.crowding_df.loc[self.crowding_df['SYSTEM'] == "SF Muni Local", 'ivtt_hours'].sum() \
                                            +  self.crowding_df.loc[self.crowding_df['SYSTEM'] == "SF Muni Metro", 'effective_ivtt_metrolinx_max2pt5'].sum() \
                                            -  self.crowding_df.loc[self.crowding_df['SYSTEM'] == "SF Muni Metro", 'ivtt_hours'].sum() \

        daily_results[(cat1,cat2,'VTA LRT')] = self.crowding_df.loc[self.crowding_df['SYSTEM'] == "VTA LRT", 'effective_ivtt_metrolinx_max2pt5'].sum() \
                                             - self.crowding_df.loc[self.crowding_df['SYSTEM'] == "VTA LRT", 'ivtt_hours'].sum()


        daily_results[(cat1,cat2,'AC Transit')] = \
                        self.crowding_df.loc[self.crowding_df['SYSTEM'] == "AC Transit", 'effective_ivtt_metrolinx_max2pt5'].sum() \
                      - self.crowding_df.loc[self.crowding_df['SYSTEM'] == "AC Transit", 'ivtt_hours'].sum()

        daily_results[(cat1,cat2,'Other')] = \
                             self.crowding_df['effective_ivtt_metrolinx_max2pt5'].sum() - self.crowding_df['ivtt_hours'].sum() \
                          - daily_results[(cat1,cat2,'BART (incl eBART)')] \
                          - daily_results[(cat1,cat2,'SF Muni')] \
                          - daily_results[(cat1,cat2,'Caltrain')] \
                          - daily_results[(cat1,cat2,'VTA LRT')] \
                          - daily_results[(cat1,cat2,'AC Transit')] \
                          - (self.crowding_df.loc[self.crowding_df['SYSTEM'] == "VTA Shuttle", 'effective_ivtt_metrolinx_max2pt5'].sum() \
                                            -  self.crowding_df.loc[self.crowding_df['SYSTEM'] == "VTA Shuttle", 'ivtt_hours'].sum()) \
                          - (self.crowding_df.loc[self.crowding_df['SYSTEM'] == "Broadway Shuttle", 'effective_ivtt_metrolinx_max2pt5'].sum() \
                                            -  self.crowding_df.loc[self.crowding_df['SYSTEM'] == "Broadway Shuttle", 'ivtt_hours'].sum()) \
                          - (self.crowding_df.loc[self.crowding_df['SYSTEM'] == "Caltrain Shuttle", 'effective_ivtt_metrolinx_max2pt5'].sum() \
                                            -  self.crowding_df.loc[self.crowding_df['SYSTEM'] == "Caltrain Shuttle", 'ivtt_hours'].sum()) \
                          - (self.crowding_df.loc[self.crowding_df['SYSTEM'] == "Stanford Shuttle", 'effective_ivtt_metrolinx_max2pt5'].sum() \
                                            -  self.crowding_df.loc[self.crowding_df['SYSTEM'] == "Stanford Shuttle", 'ivtt_hours'].sum()) \
                          - (self.crowding_df.loc[self.crowding_df['SYSTEM'] == "Emery Go Round", 'effective_ivtt_metrolinx_max2pt5'].sum() \
                                            -  self.crowding_df.loc[self.crowding_df['SYSTEM'] == "Emery Go Round", 'ivtt_hours'].sum())
                            # above formula removes all free shuttles from transit crowding calculation


        cat2            = 'Vehicle Ownership'
        daily_results[(cat1,cat2,'Total')] = self.autos_owned['total autos'].sum()


        ######################################################################################

        cat1 = "Environmental Benefits"

        cat2            = 'CO2 (metric tons)'
        daily_results[(cat1,cat2,'CO2')] = vmt_byclass.loc[:,'CO2'  ].sum()

        if 'base_dir' in self.config.keys():
            cat2            = 'Natural Land (acres)'
            daily_results[(cat1,cat2,'Wetland')] = self.natural_land.get('wetland (acres)')
            daily_results[(cat1,cat2,'Forestland')] = self.natural_land.get('forestland (acres)')
            daily_results[(cat1,cat2,'Pastureland')] = self.natural_land.get('pastureland (acres)')
            daily_results[(cat1,cat2,'Agricultural Land')] = self.natural_land.get('agricultural land (acres)')

        ######################################################################################

        cat1            = "Safety Benefits"


        # Collisions

        cat2            = 'Fatalies due to Collisions'
        daily_results[(cat1,cat2,'Motor Vehicle'       )] = vmt_byclass.loc[:,'Motor Vehicle Fatality'].sum()
        daily_results[(cat1,cat2,'Walk'                )] = vmt_byclass.loc[:,'Walk Fatality'         ].sum()
        daily_results[(cat1,cat2,'Bike'                )] = vmt_byclass.loc[:,'Bike Fatality'         ].sum()
        #daily_results[(cat1,cat2,'CRF-based reduction' )] = -self.collisions_switrs.get('annual_fatalities_reduction')

        cat2            = 'Injuries due to Collisions'
        daily_results[(cat1,cat2,'Motor Vehicle')] = vmt_byclass.loc[:,'Motor Vehicle Injury'  ].sum()
        daily_results[(cat1,cat2,'Walk'         )] = vmt_byclass.loc[:,'Walk Injury'           ].sum()
        daily_results[(cat1,cat2,'Bike'         )] = vmt_byclass.loc[:,'Bike Injury'           ].sum()
        #daily_results[(cat1,cat2,'CRF-based reduction' )] = -self.collisions_switrs.get('annual_injuries_reduction')

        cat2           = 'Property Damage Only (PDO) Collisions'
        daily_results[(cat1,cat2,'Property Damage')] = vmt_byclass.loc[:,'Motor Vehicle Property'].sum()

        if 'base_dir' in self.config.keys():
            cat2            = 'CRF-based reduction in Collisions'
            daily_results[(cat1,cat2,'Fatalities')] = -self.collisions_switrs.get('annual_fatalities_reduction')
            daily_results[(cat1,cat2,'Injuries')] = -self.collisions_switrs.get('annual_injuries_reduction')
            #except:
            #    daily_results[(cat1,cat2,'Fatalities')] = 0
             #   daily_results[(cat1,cat2,'Injuries')] = 0


        ######################################################################################
        cat1            = "Health Benefits"

        # Pollutants

        cat2            = 'PM2.5 (tons)'
        daily_results[(cat1,cat2,'PM2.5 Tailpipe Gasoline')] = \
            vmt_byclass.loc[:,'Gas_PM2.5'].sum()*RunResults.METRIC_TONS_TO_US_TONS
        daily_results[(cat1,cat2,'PM2.5 Tailpipe Diesel'  )] = \
            vmt_byclass.loc[:,'Diesel_PM2.5'].sum()*RunResults.METRIC_TONS_TO_US_TONS

        # this will get updated if base results
        #daily_results[(cat1,cat2,'PM2.5 Road Dust')] = 0
        #            (vmt_byclass.loc[['da','dat','s2','s2t','s3','s3t','daav','s2av','s3av'],'VMT'].sum() + \
        #     vmt_byclass.loc[['sm','smt','hv','hvt'],'VMT'].sum()) * RunResults.PM25_ROADDUST*RunResults.GRAMS_TO_US_TONS

        daily_results[cat1,cat2,'PM2.5 Road Dust'] = (vmt_byclass.loc[['da','dat','s2','s2t','s3','s3t'],'VMT'].sum() + \
                                                      vmt_byclass.loc[['daav','s2av','s3av'],'VMT'].sum()      +\
                                                      vmt_byclass.loc[['sm','smt','hv','hvt'],'VMT'].sum()) * \
                                                         RunResults.PM25_ROADDUST*RunResults.GRAMS_TO_US_TONS

        daily_results[(cat1,cat2,'PM2.5 Brake & Tire Wear')] = \
            vmt_byclass.loc[:,'PM2.5_wear'].sum()*RunResults.METRIC_TONS_TO_US_TONS


        cat2            = 'Other Air Pollutants'
        daily_results[(cat1,cat2,'NOX (tons)')] = vmt_byclass.loc[:,'W_NOx'].sum()*RunResults.METRIC_TONS_TO_US_TONS + \
            vmt_byclass.loc[:,'S_NOx'].sum()*RunResults.METRIC_TONS_TO_US_TONS
        daily_results[(cat1,cat2,'SO2 (tons)')] = vmt_byclass.loc[:,'SOx'  ].sum()*RunResults.METRIC_TONS_TO_US_TONS

        # http://en.wikipedia.org/wiki/Volatile_organic_compound
        daily_results[(cat1,cat2,'VOC: Acetaldehyde (metric tons)' )] = vmt_byclass.loc[:,'Acetaldehyde'  ].sum()*RunResults.METRIC_TONS_TO_US_TONS
        daily_results[(cat1,cat2,'VOC: Benzene (metric tons)'      )] = vmt_byclass.loc[:,'Benzene'       ].sum()*RunResults.METRIC_TONS_TO_US_TONS
        daily_results[(cat1,cat2,'VOC: 1,3-Butadiene (metric tons)')] = vmt_byclass.loc[:,'Butadiene'     ].sum()*RunResults.METRIC_TONS_TO_US_TONS
        daily_results[(cat1,cat2,'VOC: Formaldehyde (metric tons)' )] = vmt_byclass.loc[:,'Formaldehyde'  ].sum()*RunResults.METRIC_TONS_TO_US_TONS
        daily_results[(cat1,cat2,'All other VOC (metric tons)'     )] = vmt_byclass.loc[:,'ROG'].sum()*RunResults.METRIC_TONS_TO_US_TONS \
            - daily_results[(cat1,cat2,'VOC: Acetaldehyde (metric tons)' )] \
            - daily_results[(cat1,cat2,'VOC: Benzene (metric tons)'      )] \
            - daily_results[(cat1,cat2,'VOC: 1,3-Butadiene (metric tons)')] \
            - daily_results[(cat1,cat2,'VOC: Formaldehyde (metric tons)' )]



        # Active Transport

        cat2         = 'Avg Minutes Active Transport per Person'
        active_cat2  = cat2
        nonmot_byclass_2064  = self.nonmot_times.loc['20-64'].sum(level='Mode')  # person trips
        nonmot_byclass_2074  = self.nonmot_times.loc['20-74'].sum(level='Mode')  # person trips
        transit_byaceg_2074  = self.transit_times_by_acc_mode_egr.loc['20-74'].sum(level=['Access','Egress'])

        daily_results[(cat1,cat2,'Bike (20-64yrs cyclists)'         )] = nonmot_byclass_2064.loc['Bike','Total Time (Hours)'] * 60.0 / self.unique_active_travelers['unique_cyclists_2064']
        daily_results[(cat1,cat2,'Walk (20-74yrs walkers)'          )] = nonmot_byclass_2074.loc['Walk','Total Time (Hours)'] * 60.0 / self.unique_active_travelers['unique_walkers_2074' ]
        daily_results[(cat1,cat2,'Transit (20-74yrs transit riders)')] = (transit_byaceg_2074.loc[:,'Walk acc & egr hours'].sum() + \
                                                           transit_byaceg_2074.loc[:,'Aux walk hours'].sum()) * 60.0 / self.unique_active_travelers['unique_transiters_2074']

        cat2         = 'Active Individuals (Morbidity)'
        # Really these are active addults
        daily_results[(cat1,cat2,'Total'  )] = self.unique_active_travelers['number_active_adults']

        cat2         = 'Activity: Est Proportion Deaths Averted'
        epda_cat2    = cat2
        # Estimate of proportion of deaths prevented as a result of activity
        # 5.0 is to make it weekly
        daily_results[(cat1,cat2,'Bike (20-64yrs cyclists)'         )] = (daily_results[(cat1,active_cat2,'Bike (20-64yrs cyclists)'         )]*5.0/RunResults.CYCLING_REF_WEEKLY_MIN) * (1.0-RunResults.CYCLING_RELATIVE_RISK)
        daily_results[(cat1,cat2,'Walk (20-74yrs walkers)'          )] = (daily_results[(cat1,active_cat2,'Walk (20-74yrs walkers)'          )]*5.0/RunResults.WALKING_REF_WEEKLY_MIN) * (1.0-RunResults.WALKING_RELATIVE_RISK)
        daily_results[(cat1,cat2,'Transit (20-74yrs transit riders)')] = (daily_results[(cat1,active_cat2,'Transit (20-74yrs transit riders)')]*5.0/RunResults.WALKING_REF_WEEKLY_MIN) * (1.0-RunResults.WALKING_RELATIVE_RISK)

        cat2         = 'Activity: Est Deaths Averted (Mortality)'
        daily_results[(cat1,cat2,'Bike (20-64yrs cyclists)'         )] = daily_results[(cat1,epda_cat2,'Bike (20-64yrs cyclists)'         )]*(float(RunResults.BAY_AREA_MORTALITY_RATE_2064YRS)/100000.0)*self.unique_active_travelers['unique_cyclists_2064'  ]
        daily_results[(cat1,cat2,'Walk (20-74yrs walkers)'          )] = daily_results[(cat1,epda_cat2,'Walk (20-74yrs walkers)'          )]*(float(RunResults.BAY_AREA_MORTALITY_RATE_2074YRS)/100000.0)*self.unique_active_travelers['unique_walkers_2074'   ]
        daily_results[(cat1,cat2,'Transit (20-74yrs transit riders)')] = daily_results[(cat1,epda_cat2,'Transit (20-74yrs transit riders)')]*(float(RunResults.BAY_AREA_MORTALITY_RATE_2074YRS)/100000.0)*self.unique_active_travelers['unique_transiters_2074']

        # Noise
        cat2            = 'Noise'
        daily_results[(cat1,cat2,'Auto VMT')] = \
            vmt_byclass.loc[['da','dat','s2','s2t','s3','s3t','daav','s2av','s3av'],'VMT'].sum()
        # computed will get overwritten if base results
        daily_results[(cat1,cat2,'Truck VMT - Computed')] = \
            vmt_byclass.loc[['sm','smt','hv','hvt'],'VMT'].sum()



        ######################################################################################
        cat1            = 'Travel Time Stats (for reference only)'


        cat2            = 'Auto Hours (Person Hours)'
        daily_results[(cat1,cat2,'SOV (PHT)'  )] = vmt_byclass.loc[['da','dat','daav'],'VHT'].sum()
        daily_results[(cat1,cat2,'HOV2 (PHT)' )] = vmt_byclass.loc[['s2','s2t','s2av'],'VHT'].sum()*2
        daily_results[(cat1,cat2,'HOV3+ (PHT)')] = vmt_byclass.loc[['s3','s3t','s3av'],'VHT'].sum()*3.5

        quick_summary['Auto SOV Hours (Person Hours)'] = vmt_byclass.loc[['da','dat','daav'],'VHT'].sum()
        quick_summary['Auto HOV2 Hours (Person Hours)'] = vmt_byclass.loc[['s2','s2t','s2av'],'VHT'].sum()*2
        quick_summary['Auto HOV3 Hours (Person Hours)'] = vmt_byclass.loc[['s3','s3t','s3av'],'VHT'].sum()*3.5
        quick_summary['Auto Hours (Person Hours)'] = vmt_byclass.loc[['da','dat','daav'],'VHT'].sum() + \
                                                     vmt_byclass.loc[['s2','s2t','s2av'],'VHT'].sum()*2 + \
                                                     vmt_byclass.loc[['s3','s3t','s3av'],'VHT'].sum()*3.5

        cat2            = 'Truck Hours'
        # computed will get overwritten if base results
        daily_results[(cat1,cat2,'Truck (Computed VHT)')] = vmt_byclass.loc[['sm','smt','hv','hvt'],'VHT'].sum()
        daily_results[(cat1,cat2,'Truck (Modeled VHT)' )] = vmt_byclass.loc[['sm','smt','hv','hvt'],'VHT'].sum()
        # quick summary
        quick_summary['Vehicle Hours traveled -- SOV']        = vmt_byclass.loc[['da','dat','daav'],'VHT'].sum()
        quick_summary['Vehicle Hours traveled -- HOV2']        = vmt_byclass.loc[['s2','s2t','s2av'],'VHT'].sum()
        quick_summary['Vehicle Hours traveled -- HOV3'] =        vmt_byclass.loc[['s3','s3t','s3av'],'VHT'].sum()
        quick_summary['Vehicle Hours traveled -- Trucks']        = vmt_byclass.loc[['sm','smt','hv','hvt'],'VHT'].sum()


        # These are from vehicle hours -- make them person hours
        cat2            = 'Non-Recurring Freeway Delay (Hours)'
        daily_results[(cat1,cat2,'Auto (Person Hours)')] = \
            vmt_byclass.loc[['da','dat','daav'],'Non-Recurring Freeway Delay'].sum()   +\
            vmt_byclass.loc[['s2','s2t','s2av'],'Non-Recurring Freeway Delay'].sum()*2 +\
            vmt_byclass.loc[['s3','s3t','s3av'],'Non-Recurring Freeway Delay'].sum()*3.5

        # computed will get overwritten if base results
        daily_results[(cat1,cat2,'Truck (Computed VH)')] = \
            vmt_byclass.loc[['sm','smt','hv','hvt'],'Non-Recurring Freeway Delay'].sum()
        daily_results[(cat1,cat2,'Truck (Modeled VH)')] = \
            vmt_byclass.loc[['sm','smt','hv','hvt'],'Non-Recurring Freeway Delay'].sum()
        # quick summary
        quick_summary['Vehicle hours of non-recurring delay - passenger'       ]   = \
            vmt_byclass.loc[['da','dat','s2','s2t','s3','s3t','daav','s2av','s3av'], 'Non-Recurring Freeway Delay'].sum()
        quick_summary['Vehicle hours of non-recurring delay - commercial (raw)']   = \
            vmt_byclass.loc[['sm','smt','hv','hvt'],            'Non-Recurring Freeway Delay'].sum()


        cat2            = 'Transit In-Vehicle (Hours)'
        daily_results[(cat1,cat2,'Local Bus'       )] = transit_byclass.loc['loc','In-vehicle hours']
        daily_results[(cat1,cat2,'Light Rail/Ferry')] = transit_byclass.loc['lrf','In-vehicle hours']
        daily_results[(cat1,cat2,'Express Bus'     )] = transit_byclass.loc['exp','In-vehicle hours']
        daily_results[(cat1,cat2,'Heavy Rail'      )] = transit_byclass.loc['hvy','In-vehicle hours']
        daily_results[(cat1,cat2,'Commuter Rail'   )] = transit_byclass.loc['com','In-vehicle hours']
        quick_summary['Transit person hours of travel -- in-vehicle']     = transit_byclass.loc[:,'In-vehicle hours'    ].sum()
        quick_summary['Transit person hours of travel -- out-of-vehicle'] = transit_byclass.loc[:,'Out-of-vehicle hours'].sum()

        cat2            = 'Transit Out-of-Vehicle (Hours)'
        daily_results[(cat1,cat2,'Walk Access+Egress' )] = transit_byclass.loc[:,'Walk acc & egr hours'].sum() + \
                                                     transit_byclass.loc[:,'Aux walk hours'].sum()
        daily_results[(cat1,cat2,'Drive Access+Egress')] = transit_byclass.loc[:,'Drive acc & egr hours'].sum()
        daily_results[(cat1,cat2,'Wait'               )] = transit_byclass.loc[:,'Init wait hours'].sum() + \
                                                     transit_byclass.loc[:,'Xfer wait hours'].sum()


        # Out-of-Vehicle adjustment
        auto_person_trips    = auto_byclass.loc[['da','datoll','da_av_toll', 'da_av_notoll',\
                                                'sr2','sr2toll','s2_av_toll', 's2_av_notoll',\
                                                'sr3','sr3toll','s3_av_toll', 's3_av_notoll'],'Daily Person Trips'].sum()
        transit_person_trips = transit_byclass.loc[:,'Transit Trips'].sum()
        quick_summary['Transit person trips'] = transit_person_trips

        # If this is base dir, ovtt adjustment comes from project
        if self.is_base_dir:
            # self.ovtt_adjustment should already be set below if we're using this as a base for a scenario
            try:
                print "ovtt_adjustment = ", self.ovtt_adjustment
            except AttributeError:
                self.ovtt_adjustment = 0
            pass
        elif self.config.loc['Project Mode'] in ['com','hvy','exp','lrf','loc']:
            self.ovtt_adjustment = transit_byclass.loc[self.config.loc['Project Mode'],'Out-of-vehicle hours'] / \
                                   transit_byclass.loc[self.config.loc['Project Mode'],'Transit Trips']

        elif self.config.loc['Project Mode'] == 'road':
            self.ovtt_adjustment = transit_byclass.loc[:,'Out-of-vehicle hours'].sum() / \
                                   transit_byclass.loc[:,'Transit Trips'].sum()
        else:
            raise Exception("Invalid Project Mode:'%s'; Should be one of 'road','com','hvy','exp','lrf','loc'" % \
                            self.config.loc['Project Mode'])
        # tell the base
        if self.base_results:
            self.base_results.ovtt_adjustment = self.ovtt_adjustment

        # OVTT adjustment multiplier
        if self.config.loc['Project Mode'] in ['com','hvy','exp','lrf','loc']:
             # Adjustment for transit: auto person trips x avg OVTT in Scenario
             daily_results[(cat1,cat2,'OVTT Adjustment')] = self.ovtt_adjustment * auto_person_trips

        elif self.config.loc['Project Mode'] == 'road':
            # Adjustment for road: transit person trips x avg OVTT in Scenario
            daily_results[(cat1,cat2,'OVTT Adjustment')] = self.ovtt_adjustment * transit_person_trips

        cat2            = 'Walk/Bike (Hours)'
        daily_results[(cat1,cat2,'Walk')] = nonmot_byclass.loc['Walk','Total Time (Hours)']
        daily_results[(cat1,cat2,'Bike')] = nonmot_byclass.loc['Bike','Total Time (Hours)']



        cat1            = 'Other Travel Metrics (for reference only)'

        cat2            = 'VMT by class'
        daily_results[(cat1,cat2,'Auto non-AV' )]           = vmt_byclass.loc[['da','dat','s2','s2t','s3','s3t'],'VMT'].sum()
        daily_results[(cat1,cat2,'Auto AV' )]               = vmt_byclass.loc[['daav','s2av','s3av'],'VMT'].sum()
        # computed will get overwritten if base results
        daily_results[(cat1,cat2,'Truck - Computed')]       = vmt_byclass.loc[['sm','smt','hv','hvt'],'VMT'].sum()
        #daily_results[(cat1,cat2,'Truck - Modeled')]        = vmt_byclass.loc[['sm','smt','hv','hvt'],'VMT'].sum()
        #daily_results[(cat1,cat2,'Truck from Trips+Skims')] = auto_byclass.loc['truck','Vehicle Miles']
        # quick summary
        quick_summary['VMT -- passenger non-AV vehicles']   = vmt_byclass.loc[['da','dat','s2','s2t','s3','s3t'],'VMT'].sum()
        quick_summary['VMT -- passenger AV vehicles']       = vmt_byclass.loc[['daav','s2av','s3av'],'VMT'].sum()
        quick_summary['VMT -- passenger all vehicles']       = vmt_byclass.loc[['da','dat','s2','s2t','s3','s3t','daav','s2av','s3av'],'VMT'].sum()
        quick_summary['VMT -- trucks'] = vmt_byclass.loc[['sm','smt','hv','hvt'],'VMT'].sum()
        quick_summary['VMT -- all vehicles'] = vmt_byclass.loc[['da','dat','s2','s2t','s3','s3t','daav','s2av','s3av','sm','smt','hv','hvt'],'VMT'].sum()


        cat2            = 'VMT by mode'
        daily_results[(cat1,cat2,'Auto SOV'  )] = auto_byclass.loc[['da' ,'datoll', 'da_av_toll', 'da_av_notoll',\
                                                                    'da_ix','datoll_ix','da_air','datoll_air'],'Vehicle Miles'].sum()
        daily_results[(cat1,cat2,'Auto HOV2' )] = auto_byclass.loc[['sr2','sr2toll', 's2_av_toll', 's2_av_notoll',\
                                                                     'sr2_ix','sr2toll_ix', 'sr2_air','sr2toll_air'],'Vehicle Miles'].sum()
        daily_results[(cat1,cat2,'Auto HOV3+')] = auto_byclass.loc[['sr3','sr3toll', 's3_av_toll', 's3_av_notoll',\
                                                                     'sr3_ix','sr3toll_ix', 'sr3_air','sr3toll_air'],'Vehicle Miles'].sum()
        daily_results[(cat1,cat2,'Auto TNC/Taxi')] = auto_byclass.loc[['tnc_single', 'tnc_shared', 'taxi'],'Vehicle Miles'].sum()
        daily_results[(cat1,cat2,'Auto ZOV')] = auto_byclass.loc[['owned_zpv', 'zpv_tnc'],'Vehicle Miles'].sum()
        daily_results[(cat1,cat2,'Truck')] = auto_byclass.loc['truck','Vehicle Miles'].sum()

        quick_summary['VMT -- TNC']   = auto_byclass.loc[['tnc_single', 'tnc_shared'],'Vehicle Miles'].sum()
        quick_summary['VMT -- ZOV']       = auto_byclass.loc[['owned_zpv', 'zpv_tnc'],'Vehicle Miles'].sum()


        total_autoVMT = daily_results[(cat1,cat2,'Auto SOV')] + \
                          daily_results[(cat1,cat2,'Auto HOV2')] + \
                          daily_results[(cat1,cat2,'Auto HOV3+')] + \
                          daily_results[(cat1,cat2,'Auto TNC/Taxi')] + \
                          daily_results[(cat1,cat2,'Auto ZOV')]
        total_VMT = total_autoVMT + daily_results[(cat1,cat2,'Truck')]


        cat2            = 'Vehicle Trips by mode (incl. IX and Air)'
        daily_results[(cat1,cat2,'Auto SOV'  )] = auto_byclass.loc[['da' ,'datoll', 'da_av_toll', 'da_av_notoll',\
                                                                    'da_ix','datoll_ix','da_air','datoll_air'],'Daily Vehicle Trips'].sum()
        daily_results[(cat1,cat2,'Auto HOV2' )] = auto_byclass.loc[['sr2','sr2toll', 's2_av_toll', 's2_av_notoll',\
                                                                     'sr2_ix','sr2toll_ix','sr2_air','sr2toll_air'],'Daily Vehicle Trips'].sum()
        daily_results[(cat1,cat2,'Auto HOV3+')] = auto_byclass.loc[['sr3','sr3toll', 's3_av_toll', 's3_av_notoll',\
                                                                     'sr3_ix','sr3toll_ix', 'sr3_air','sr3toll_air'],'Daily Vehicle Trips'].sum()
        daily_results[(cat1,cat2,'Auto TNC/Taxi')] = auto_byclass.loc[['tnc_single', 'tnc_shared', 'taxi'],'Daily Vehicle Trips'].sum()
        daily_results[(cat1,cat2,'Auto ZOV')] = auto_byclass.loc[['owned_zpv', 'zpv_tnc'],'Daily Vehicle Trips'].sum()
        #daily_results[(cat1,cat2,'Transit (Drive) Trips')] = transit_byaceg.loc[[('wlk','drv'),('drv','wlk')],'Transit Trips'].sum()
        #daily_results[(cat1,cat2,'Transit (Walk) Trips')] = transit_byaceg.loc[('wlk','wlk'),'Transit Trips'].sum()
        #daily_results[(cat1,cat2,'Walk')] = nonmot_byclass.loc['Walk','Daily Trips']
        #daily_results[(cat1,cat2,'Bike')] = nonmot_byclass.loc['Bike','Daily Trips']

        cat2            = 'Non-Household Vehicle Trips'
        daily_results[(cat1,cat2,'Interregional IX/EX' )] = auto_byclass.loc[['da_ix','datoll_ix',\
                                                                     'sr2_ix','sr2toll_ix', 'sr3_ix','sr3toll_ix'],'Daily Vehicle Trips'].sum()
        daily_results[(cat1,cat2,'Airport'  )] = auto_byclass.loc[['da_air','datoll_air',\
                                                                    'sr2_air','sr2toll_air','sr3_air','sr3toll_air'],'Daily Vehicle Trips'].sum()
        daily_results[(cat1,cat2,'Truck'  )] = auto_byclass.loc[['truck'],'Daily Vehicle Trips'].sum()


        cat2            = 'Person Trips by mode (all trips)'
        daily_results[(cat1,cat2,'Auto SOV'  )] = auto_byclass.loc[['da' ,'datoll', 'da_av_toll', 'da_av_notoll',\
                                                                    'da_ix','datoll_ix','da_air','datoll_air'],'Daily Person Trips'].sum()
        daily_results[(cat1,cat2,'Auto HOV2' )] = auto_byclass.loc[['sr2','sr2toll', 's2_av_toll', 's2_av_notoll',\
                                                                     'sr2_ix','sr2toll_ix','sr2_air','sr2toll_air'],'Daily Person Trips'].sum()
        daily_results[(cat1,cat2,'Auto HOV3+')] = auto_byclass.loc[['sr3','sr3toll', 's3_av_toll', 's3_av_notoll',\
                                                                    'sr3_ix','sr3toll_ix', 'sr3_air','sr3toll_air'],'Daily Person Trips'].sum()
        daily_results[(cat1,cat2,'Auto TNC/Taxi')] = auto_byclass.loc[['tnc_single', 'tnc_shared', 'taxi'],'Daily Person Trips'].sum()
        daily_results[(cat1,cat2,'Auto ZOV')] = auto_byclass.loc[['owned_zpv', 'zpv_tnc'],'Daily Person Trips'].sum()
        daily_results[(cat1,cat2,'Transit (Drive) Trips')] = transit_byaceg.loc[[('wlk','drv'),('drv','wlk')],'Transit Trips'].sum()
        daily_results[(cat1,cat2,'Transit (Walk) Trips')] = transit_byaceg.loc[('wlk','wlk'),'Transit Trips'].sum()
        daily_results[(cat1,cat2,'Walk')] = nonmot_byclass.loc['Walk','Daily Trips']
        daily_results[(cat1,cat2,'Bike')] = nonmot_byclass.loc['Bike','Daily Trips']



        total_autotrips = daily_results[(cat1,cat2,'Auto SOV')] + \
                          daily_results[(cat1,cat2,'Auto HOV2')] + \
                          daily_results[(cat1,cat2,'Auto HOV3+')] + \
                          daily_results[(cat1,cat2,'Auto TNC/Taxi')] + \
                          daily_results[(cat1,cat2,'Auto ZOV')]
        total_transittrips = daily_results[(cat1,cat2,'Transit (Drive) Trips')] + \
                          daily_results[(cat1,cat2,'Transit (Walk) Trips')]
        total_walktrips = daily_results[(cat1,cat2,'Walk')]
        total_biketrips = daily_results[(cat1,cat2,'Bike')]

        #daily_results[(cat1,cat2,'Truck')] = auto_byclass.loc['truck','Daily Vehicle Trips'].sum()

        quick_summary['Person trips (total)'] = auto_byclass.loc[['da' ,'datoll', 'da_av_toll', 'da_av_notoll', \
                                                                    'da_ix','datoll_ix','da_air','datoll_air', \
                                                                    'sr2','sr2toll', 's2_av_toll', 's2_av_notoll', \
                                                                    'sr2_ix','sr2toll_ix', 'sr2_air','sr2toll_air', \
                                                                    'sr3','sr3toll', 's3_av_toll', 's3_av_notoll', \
                                                                    'sr3_ix','sr3toll_ix', 'sr3_air','sr3toll_air'],'Daily Person Trips'].sum() + \
                                                transit_byclass.loc[:,'Transit Trips'].sum() + \
                                                nonmot_byclass.loc[:,'Daily Trips'].sum()



        # Vehicles Owned
        cat2            = 'Vehicle Ownership (Modeled)'
        daily_results[(cat1,cat2,'Total')] = self.autos_owned['total autos'].sum()
        quick_summary['Vehicle Ownership'] = self.autos_owned['total autos'].sum()

        # Vehicles Owned - estimated from auto trips
        cat2            = 'Vehicle Ownership (Est. from Auto Trips)'
        daily_results[(cat1,cat2,'Total')] =total_autotrips*RunResults.ANNUALIZATION/RunResults.YEARLY_AUTO_TRIPS_PER_AUTO


        cat2            = 'Operating Costs ($2000)'
        daily_results[(cat1,cat2,'Auto Households' )] = \
            0.01*auto_byclass.loc[['da','datoll','da_av_toll', 'da_av_notoll',\
                                    'sr2','sr2toll','s2_av_toll', 's2_av_notoll'\
                                    'sr3','sr3toll', 's3_av_toll', 's3_av_notoll'],'Total Cost'].sum()
        daily_results[(cat1,cat2,'Auto Households ZOV' )] = \
            0.01*auto_byclass.loc['owned_zpv','Total Cost'].sum()
        daily_results[(cat1,cat2,'Auto IX/EX' )] = \
            0.01*auto_byclass.loc[['da_ix','datoll_ix','sr2_ix','sr2toll_ix','sr3_ix','sr3toll_ix'],'Total Cost'].sum()
        daily_results[(cat1,cat2,'Auto AirPax' )] = \
            0.01*auto_byclass.loc[['da_air','datoll_air','sr2_air','sr2toll_air','sr3_air','sr3toll_air'],'Total Cost'].sum()
        daily_results[(cat1,cat2,'Auto TNC/Taxi' )] = \
            0.01*auto_byclass.loc[['tnc_single', 'tnc_shared', 'taxi'],'Total Cost'].sum()
        daily_results[(cat1,cat2,'Auto TNC/Taxi ZOV' )] = \
            max(0.01*auto_byclass.loc['zpv_tnc', 'Total Cost'].sum(),1)

        # computed will get overwritten if base results
        daily_results[(cat1,cat2,'Truck - Computed')] = self.roadways_df['total truck cost'].sum()
        #daily_results[(cat1,cat2,'Truck - Modeled')]  = self.roadways_df['total truck cost'].sum()


        # Parking
        cat2            = 'Parking Costs'
        for countynum,countyname in RunResults.COUNTY_NUM_TO_NAME.iteritems():
            daily_results[(cat1,cat2,'($2000) Work Tours to %s'     % countyname)] = \
                self.parking_costs.loc[(self.parking_costs.parking_category=='Work'    )&
                                       (self.parking_costs.dest_county     ==countynum ),  'parking_cost'].sum()
        for countynum,countyname in RunResults.COUNTY_NUM_TO_NAME.iteritems():
            daily_results[(cat1,cat2,'($2000) Non-Work Tours to %s' % countyname)] = \
                self.parking_costs.loc[(self.parking_costs.parking_category=='Non-Work')&
                                       (self.parking_costs.dest_county     ==countynum ),  'parking_cost'].sum()


        # Transit Crowding

        cat2            = 'Transit Crowding Penalty Hours'

        transit_systems = ['BART', 'EBART','Oakland Airport Connector', 'Caltrain',  'SMART',\
                             'SF MUNI', 'SF Muni Metro',  'SF Muni Local', 'SF Muni Cable Car' ,\
                            'AC Transit Transbay', 'AC Transit Local','AC Transit', \
                            'VTA LRT', 'VTA Express', 'VTA Local', 'SamTrans', 'SamTrans Local', 'Dumbarton Express',\
                           'Golden Gate Transit Expre','Golden Gate Transit Local', 'County Connection Local', 'WestCAT Express','WestCAT Local',\
                           'Vallejo Transit Express' , 'Fairfield and Suisun Tran', 'County Connection Express', 'Wheels Local', 'Tri Delta Transit',\
                            'VINE Express', 'VINE Local','American Canyon',\
                           'Sonoma County Transit',  'Petaluma Transit','Santa Rosa City Bus', 'Vallejo Transit',\
                            'Union City Transit', 'SMART Temporary Express', \
                            'VTA Community Bus', 'San Leandro Links', 'Palo Alto & Menlo Park Sh',\
                            #'Berkeley','VTA Shuttle','Broadway Shuttle'  'Emery Go Round', 'Stanford Shuttle', 'Caltrain Shuttle', \
                            'High Speed Rail',  'ACE', 'Amtrak Capitol Corridor', \
                            'Vallejo Baylink Ferry', 'East Bay Ferries', 'Golden Gate Ferry - Sausa', 'Golden Gate Ferry - Larks', 'Tiburon Ferry']

        for system in transit_systems:
        # crowding penalty = effective ivtt with crowding multiplier minus actual ivtt
            daily_results[(cat1,cat2,system)] = self.crowding_df.loc[self.crowding_df['SYSTEM'] == system, 'effective_ivtt_metrolinx_max2pt5'].sum() \
                                              - self.crowding_df.loc[self.crowding_df['SYSTEM'] == system, 'ivtt_hours'].sum() \


        ##########################################################################


        # A few quick summary numbers
        quick_summary['Transit boardings'] = self.transit_boards_miles.loc[:,'Daily Boardings'].sum()
        quick_summary['BART boardings'] = self.transit_boards_miles.loc['hvy','Daily Boardings'].sum()


        quick_summary['VTOLL Paths in AM - datoll']  = (float(self.auto_times.loc[('inc1','datoll'),'VTOLL nonzero AM']) +  \
                                                            float(self.auto_times.loc[('inc1','da_av_toll'),'VTOLL nonzero AM']) ) * 4
        quick_summary['VTOLL Paths in AM - sr2toll']  = (float(self.auto_times.loc[('inc1','sr2toll'),'VTOLL nonzero AM']) +  \
                                                            float(self.auto_times.loc[('inc1','s2_av_toll'),'VTOLL nonzero AM']) ) * 4
        quick_summary['VTOLL Paths in AM - sr3toll']  = (float(self.auto_times.loc[('inc1','sr3toll'),'VTOLL nonzero AM']) +  \
                                                            float(self.auto_times.loc[('inc1','s3_av_toll'),'VTOLL nonzero AM']) ) * 4
        quick_summary['VTOLL Paths in MD - datoll']  = (float(self.auto_times.loc[('inc1','datoll'),'VTOLL nonzero MD']) +  \
                                                            float(self.auto_times.loc[('inc1','da_av_toll'),'VTOLL nonzero MD']) ) * 4
        quick_summary['VTOLL Paths in MD - sr2toll']  = (float(self.auto_times.loc[('inc1','sr2toll'),'VTOLL nonzero MD']) +  \
                                                            float(self.auto_times.loc[('inc1','s2_av_toll'),'VTOLL nonzero MD']) ) * 4
        quick_summary['VTOLL Paths in MD - sr3toll']  = (float(self.auto_times.loc[('inc1','sr3toll'),'VTOLL nonzero MD']) +  \
                                                            float(self.auto_times.loc[('inc1','s3_av_toll'),'VTOLL nonzero MD']) ) * 4




        quick_summary['Peak Vehicle Volume AM Bay Bridge'] =            self.roadways_df.loc[(self.roadways_df['a'] == 2783) & (self.roadways_df['b'] ==6972), 'volAM_tot'].sum()
        quick_summary['Peak Vehicle Volume AM Southern Crossing'] =     self.roadways_df.loc[(self.roadways_df['a'] == 10821) & (self.roadways_df['b'] ==10815), 'volAM_tot'].sum()
        quick_summary['Peak Vehicle Volume AM Mid-Bay Bridge'] =        self.roadways_df.loc[(self.roadways_df['a'] == 10947) & (self.roadways_df['b'] ==10951), 'volAM_tot'].sum() \
                                                                + self.roadways_df.loc[(self.roadways_df['a'] == 10948) & (self.roadways_df['b'] ==10952), 'volAM_tot'].sum()
        quick_summary['Peak Vehicle Volume AM San Mateo Bridge'] =      self.roadways_df.loc[(self.roadways_df['a'] == 3650)  & (self.roadways_df['b'] ==6381), 'volAM_tot'].sum()
        quick_summary['Peak Vehicle Volume AM Golden Gate Bridge'] =    self.roadways_df.loc[(self.roadways_df['a'] == 7339) & (self.roadways_df['b'] ==7322), 'volAM_tot'].sum()


        quick_summary['Peak Transbay Ridership AM BART Tunnel 1'] =     self.crowding_complete_df.loc[(self.crowding_complete_df['A'] == 15510) & (self.crowding_complete_df['B'] == 15511) &
                                                                  (self.crowding_complete_df['period'] == "AM"),   'AB_VOL'].sum()
        quick_summary['Peak Transbay Ridership AM BART Tunnel 2'] =     max(self.crowding_complete_df.loc[(self.crowding_complete_df['A'] == 15553) & (self.crowding_complete_df['B'] == 15554) &\
                                                                   (self.crowding_complete_df['period'] == "AM"),   'AB_VOL'].sum() , \
                                                                self.crowding_complete_df.loc[(self.crowding_complete_df['A'] == 15553) & (self.crowding_complete_df['B'] == 15556) &\
                                                                   (self.crowding_complete_df['period'] == "AM"),   'AB_VOL'].sum() , \
                                                                self.crowding_complete_df.loc[(self.crowding_complete_df['A'] == 15553) & (self.crowding_complete_df['B'] == 20755) &\
                                                                   (self.crowding_complete_df['period'] == "AM"),   'AB_VOL'].sum() )
        quick_summary['Peak Transbay Ridership AM Reg Rail Tunnel'] =   self.crowding_complete_df.loc[(self.crowding_complete_df['A'] == 14648) & (self.crowding_complete_df['B'] == 13654) &\
                                                                  (self.crowding_complete_df['period'] == "AM"),   'AB_VOL'].sum()
        quick_summary['Peak Transbay Ridership AM AC Transit Bay Bridge'] =   self.crowding_complete_df.loc[(self.crowding_complete_df['A'] == 2783) & (self.crowding_complete_df['B'] == 6972) &\
                                                                  (self.crowding_complete_df['period'] == "AM"),   'AB_VOL'].sum()


        quick_summary['Daily Boardings - BART']    =              self.crowding_df.loc[self.crowding_df['SYSTEM'] == "BART", 'AB_BRDA'].sum() \
                                                             + self.crowding_df.loc[self.crowding_df['SYSTEM'] == "EBART", 'AB_BRDA'].sum()
        quick_summary['Daily Boardings - Caltrain']    =          self.crowding_df.loc[self.crowding_df['SYSTEM'] == "Caltrain", 'AB_BRDA'].sum()
        quick_summary['Daily Boardings - Reg Rail']    =          self.crowding_df.loc[self.crowding_df['SYSTEM'] == "Caltrain", 'AB_BRDA'].sum() \
                                                            + self.crowding_df.loc[self.crowding_df['SYSTEM'] == "Amtrak Capitol Corridor", 'AB_BRDA'].sum()
        quick_summary['Daily Boardings - AC Transit Transbay']  = self.crowding_df.loc[self.crowding_df['SYSTEM'] == "AC Transit", 'AB_BRDA'].sum()



        # do this if we can but it's not mandatory
        if 'AM path count' in transit_byclass.columns.values:
            for mode in ['com','hvy','exp','lrf','loc']:
                quick_summary['trn %s Paths in AM' % mode] = transit_byclass.loc[mode,'AM path count'].sum()
                quick_summary['trn %s Paths in MD' % mode] = transit_byclass.loc[mode,'MD path count'].sum()

        idx = pd.MultiIndex.from_tuples(daily_results.keys(),
                                        names=['category1','category2','variable_name'])
        self.daily_results = pd.Series(daily_results, index=idx)

        # figure out the small cat2s

        self.lil_cats = {}
        grouped = self.daily_results.groupby(level=['category1','category2'])
        for name,group in grouped:
            if group.sum() < 1000:
                self.lil_cats[name] = 1

        # sum to categories
        self.daily_category_results = self.daily_results.sum(level=[0,1])
        # print self.daily_category_results

        self.quick_summary = pd.Series(quick_summary)
        self.quick_summary = self.quick_summary.append(self.config)


    def calculateBenefitCosts(self, project_dir, all_projects_dir):
        """
        Compares the run results with those from the base results (if they exist),
        calculating the daily difference, annual difference, and annual benefits.

        Writes a pretty workbook into `project_dir`, and flat csv series
        into a csv in `all_projects_dir` named [Project ID].csv.
        """
        workbook_name = "BC_%s.xlsx" % self.config.loc['Project ID']
        csv_name      = "BC_%s.csv"  % self.config.loc['Project ID']
        if not self.is_base_dir and self.config.loc['base_dir']:
            print "BASE = ",self.config.loc['base_dir']
            base_str_re = re.compile("(19|20)[0-9][0-9]_05_[A-Za-z0-9]{3}[^\\\)]*")
            base_match  = base_str_re.search(self.config.loc['base_dir'])
            if base_match:
                self.config['Base Project ID'] = base_match.group(0)
            else:
                # if it doesn't conform.... just part of the path
                self.config['Base Project ID'] = self.config.loc['base_dir']

            self.config['Project Compare ID'] = "%s vs %s" % (self.config.loc['Project ID'], self.config['Base Project ID'])
            # print "base_match = [%s]" % base_match.group(0)
            workbook_name = "BC_%s_base%s.xlsx" % (self.config.loc['Project ID'], self.config['Base Project ID'])
            csv_name      = "BC_%s_base%s.csv"  % (self.config.loc['Project ID'], self.config['Base Project ID'])

        project_folder_name = project_dir.split('\\OUTPUT')[0]
        BC_detail_workbook = os.path.join(project_folder_name, workbook_name)
        workbook        = xlsxwriter.Workbook(BC_detail_workbook)

        scen_minus_base = self.writeBCWorksheet(workbook)

        if self.base_dir:
            if self.config.loc['Compare'] == 'baseline-scenario':
                base_minus_scen = self.writeBCWorksheet(workbook, scen_minus_baseline=False)
        workbook.close()
        print("Wrote the BC workbook %s" % BC_detail_workbook)



        # writing simple csv file with all bc metrics

        if self.base_dir:
            bc_metrics = None

            #PBA2040 bc_metrics
            if self.config.loc['Compare'] == 'scenario-baseline':
                bc_metrics = scen_minus_base
            elif self.config.loc['Compare'] == 'baseline-scenario':
                bc_metrics = base_minus_scen

            idx = pd.MultiIndex.from_tuples(bc_metrics.keys(),
                                            names=['category1','category2','category3','variable_name'])
            self.bc_metrics = pd.Series(bc_metrics, index=idx)


            #############################################
            # Note: All code below until the next row of #s is dependent on position of cells in the worksheet.
            #       If cell positions are changed in the functions that create the worksheet, the following code
            #       will have to be adapted accordingly.

            # Getting Lifecycle values from just created workbook
            # Need to first open and save the workbook so all formulas get calculated
            app = xl.App(visible=False)
            book = app.books.open(BC_detail_workbook)
            book.save()
            book.close()
            app.kill()
            df_lifecycleben = pd.read_excel(BC_detail_workbook, sheet_name='benefit_streams', header=None)
            df_lifecycleben =  df_lifecycleben.drop(df_lifecycleben.index[[0,1,2,3,4]])
            df_lifecycleben = df_lifecycleben[[0,1,2,4]]
            df_lifecycleben.insert(3, 'variable', 'Lifecycle Benefits 2060 (2019$)')
            df_lifecycleben.columns = ['category1', 'category2','category3','variable_name','values']
            df_lifecycleben = df_lifecycleben.set_index(['category1', 'category2','category3','variable_name'])
            lifecycle_ben = df_lifecycleben.T.iloc[0]
            self.bc_metrics = self.bc_metrics.append(lifecycle_ben)


            # Getting highest level b/c metrics from just created b/c workbook
            bc_overall_tuples = [('bc_overall', 'Horizon Year', 'bc_overall','Total Horizon Yr Benefit (2019$)'),\
                                  ('bc_overall', 'Horizon Year', 'bc_overall','Total Horizon Yr Cost (2019$)'),\
                                  ('bc_overall', 'Horizon Year', 'bc_overall', 'B/C Ratio'),\
                                  ('bc_overall', '2060', 'bc_overall','Total Lifecycle Benefit (2019$)'),\
                                  ('bc_overall', '2060', 'bc_overall', 'Total Lifecycle Cost (2019$)'),\
                                  ('bc_overall', '2060', 'bc_overall', 'B/C Ratio'),\
                                  ('bc_overall', '2080', 'bc_overall','Total Lifecycle Benefit (2019$)'),\
                                  ('bc_overall', '2080', 'bc_overall', 'Total Lifecycle Cost (2019$)'),\
                                  ('bc_overall', '2080', 'bc_overall', 'B/C Ratio'),\
                                  ('bc_overall', 'Equity', 'bc_overall','Equity Score')]
            idx = pd.MultiIndex.from_tuples(bc_overall_tuples, names=['category1','category2','category3','variable_name'])
            df_bc = pd.read_excel(BC_detail_workbook, sheet_name='scenario-baseline', header=None)
            bc_overall_array = numpy.asarray([df_bc.iloc[12,8], df_bc.iloc[13,8], df_bc.iloc[14,8],\
                                    df_bc.iloc[12,10], df_bc.iloc[13,10], df_bc.iloc[14,10],\
                                    df_bc.iloc[12,12], df_bc.iloc[13,12], df_bc.iloc[14,12],\
                                    df_bc.iloc[11,1]])       # these are the cell locations of all higher level b/c metrics
            bc_overall = pd.Series(bc_overall_array, index=idx)
            self.bc_metrics = self.bc_metrics.append(bc_overall)

            # Getting high level costs from just created b/c workbook
            costs_tuples = [('costs', 'Lifecycle Costs', '2025-60','Initial Capital'),\
                            ('costs', 'Lifecycle Costs', '2025-60','O&M'),\
                            ('costs', 'Lifecycle Costs', '2025-60','Rehab + Replacement'),\
                            ('costs', 'Lifecycle Costs', '2025-60','Residual Value'),\
                            ('costs', 'Lifecycle Costs', '2025-80','Initial Capital'),\
                            ('costs', 'Lifecycle Costs', '2025-80','O&M'),\
                            ('costs', 'Lifecycle Costs', '2025-80','Rehab + Replacement'),\
                            ('costs', 'Lifecycle Costs', '2025-80','Residual Value'),\
                            ('costs', 'YOE Costs', '2019$','Capital'),\
                            ('costs', 'YOE Costs', '2019$','O&M'),\
                            ('costs', 'Annualized Costs', '2050','Capital'),\
                            ('costs', 'Annualized Costs', '2050','O&M')]
            idx = pd.MultiIndex.from_tuples(costs_tuples, names=['category1','category2','category3','variable_name'])
            df_costs = pd.read_excel(BC_detail_workbook, sheet_name='cost_streams', header=None)
            costs_array = numpy.asarray([df_costs.iloc[2,5], df_costs.iloc[3,5], df_costs.iloc[1,9], -df_costs.iloc[2,9],\
                                         df_costs.iloc[2,6], df_costs.iloc[3,6], df_costs.iloc[1,10], -df_costs.iloc[2,10],\
                                         df_costs.iloc[1,13], df_costs.iloc[2,13],\
                                         df_costs.iloc[2,4], df_costs.iloc[3,4]])       # these are the cell locations of all higher level b/c metrics
            costs = pd.Series(costs_array, index=idx)
            self.bc_metrics = self.bc_metrics.append(costs)

            #################################################

            gp_tuples = [('Guiding Principles', 'Meets', 'All','All'),\
                         ('Guiding Principles', 'Does Not Support','All', 'All'),\
                         ('Guiding Principles', 'Principle', 'Score (0/1)', 'Affordable'),\
                         ('Guiding Principles', 'Principle', 'Score (0/1)', 'Connected'),\
                         ('Guiding Principles', 'Principle', 'Score (0/1)', 'Diverse'),\
                         ('Guiding Principles', 'Principle', 'Score (0/1)', 'Healthy'),\
                         ('Guiding Principles', 'Principle', 'Score (0/1)', 'Vibrant')]
            idx = pd.MultiIndex.from_tuples(gp_tuples, names=['category1','category2','category3','variable_name'])
            gp_array = numpy.asarray(list(self.gp.values()))
            gp = pd.Series(gp_array, index=idx)
            self.bc_metrics = self.bc_metrics.append(gp)


            #################################################

            self.bc_metrics.name = 'values'
            all_proj_filename = os.path.join(os.getcwd(), all_projects_dir, csv_name)
            self.bc_metrics.to_csv(all_proj_filename, header=True, float_format='%.5f')
            print("Wrote the bc metrics csv %s" % csv_name)

        copyfile(BC_detail_workbook, os.path.join(project_folder_name,"..","..","all_projects_bc_workbooks", workbook_name))
        print("Copied BC workbook into all_projects_bc_workbooks directory")


    def writeBCWorksheet(self, workbook, scen_minus_baseline=True):
        """
        Writes a worksheet into the workbook.
        If scen_minus_baseline, then it's the scenario - baseline.
        Otherwise it's the baseline_minus_scen
        """

        worksheet = None
        if not self.base_dir:
            worksheet       = workbook.add_worksheet('baseline')
            colA            = self
            colA_header     = "Daily"
        elif scen_minus_baseline:
            colA            = self
            colA_header     = "Daily Scenario"
            colB            = self.base_results
            colB_header     = "Daily Baseline"
            worksheet       = workbook.add_worksheet('scenario-baseline')
            diff_header     = "Scenario - Baseline"
        else:
            colA            = self.base_results
            colA_header     = "Daily Baseline"
            colB            = self
            colB_header     = "Daily Scenario"
            worksheet       = workbook.add_worksheet('baseline-scenario')

            diff_header     = "Baseline - Scenario"
        worksheet.protect()

        # these will be the daily and annual diffs, and monetized diffs
        # key = (category1, category2, category3, variable name)
        bc_metrics      = collections.OrderedDict()
        # put config in here first
        for key,val in self.config.iteritems():
            bc_metrics[(key,"","","")] = val


        # Notice row
        format_red      = workbook.add_format({'font_color':'red', 'bold':True})
        worksheet.write(0,0, "This workbook is written by the script %s.  " % os.path.realpath(__file__) +
                             "DO NOT CHANGE THE WORKBOOK, CHANGE THE SCRIPT.",
                             format_red)
        # Info rows
        format_label    = workbook.add_format({'align':'right','indent':1, 'valign':'vcenter'})
        format_highlight= workbook.add_format({'bg_color':'yellow'})
        format_highlight_file  = workbook.add_format({'bg_color':'yellow', 'font_size':8, 'text_wrap':True})
        format_highlight_money = workbook.add_format({'bg_color':'yellow',
                                                     'num_format':'_($* #,##0.0_);_($* (#,##0.0);_($* "-"_);_(@_)'})

        worksheet.write(1,0, "Project Run Dir", format_label)
        worksheet.merge_range(1,1,1,4, os.path.realpath(self.rundir), format_highlight_file)
        worksheet.set_row(1,36.0)

        # Config-based rows
        row = 2
        for key in RunResults.REQUIRED_KEYS:
            worksheet.write(row,0, key, format_label)
            config_key  = '%s' %key
            try:    val = float(self.config.loc[config_key])
            except: val = self.config.loc[config_key]
            worksheet.write(row,1, val, format_highlight)
            for col in range(2,5): worksheet.write(row,col,"",format_highlight)
            row += 1

        # Run directory
        if self.base_dir:
            worksheet.write(row,0, "Base Run Dir", format_label)
            worksheet.merge_range(row,1,row,4, os.path.realpath(self.base_dir), format_highlight_file)
            worksheet.set_row(row,36.0)


        # Header row
        row += 7 # space
        TABLE_HEADER_ROW = row
        format_header = workbook.add_format({'bg_color':'#1F497D',
                                             'font_color':'white',
                                             'bold':True,
                                             'text_wrap':True,
                                             'align':'center'})
        worksheet.write(row,0,"Benefit/Cost",format_header)
        worksheet.write(row,1,colA_header,format_header)
        if self.base_dir:
            worksheet.write(row,2,colB_header,format_header)
            worksheet.write(row,3,"Daily\n%s" % diff_header,format_header)
            worksheet.write(row,4,"Annual\n%s" % diff_header,format_header)
            worksheet.write(row,6,"Benefit Valuation\n(per unit)",format_header)
            worksheet.write(row,8,"Horizon Yr\nBenefit\n(2019$)",format_header)
            worksheet.write(row,10,"Analysis Period\nBenefit\n(2025-60)\n(2019$)",format_header)
            worksheet.write(row,12,"Analysis Period\nBenefit\n(2025-80)\n(2019$)",format_header)

        # Data rows
        row  += 1
        cat1 = None
        cat2 = None
        format_cat1     = workbook.add_format({'bold':True, 'bg_color':'#C5D9F1'})
        format_cat1_sum = workbook.add_format({'bold':True, 'bg_color':'#C5D9F1', 'num_format':'_(\$* #,##0"M"_);_(\$* (#,##0"M");_(\$* "-"??_);_(@_)'})
        format_cat2     = workbook.add_format({'bold':True, 'indent':1, 'bg_color':'#D9D9D9'})
        format_cat2_big = workbook.add_format({'bg_color':'#92D050', 'num_format':'#,##0'})
        format_cat2_lil = workbook.add_format({'bg_color':'#92D050', 'num_format':'#,##0.000'})
        format_var      = workbook.add_format({'indent':2})
        format_val_big  = workbook.add_format({'num_format':'#,##0'})
        format_val_lil  = workbook.add_format({'num_format':'#,##0.000'})

        format_cat2b_big = workbook.add_format({'bg_color':'#FCD5B4', 'num_format':'#,##0'})
        format_cat2b_lil = workbook.add_format({'bg_color':'#FCD5B4', 'num_format':'#,##0.000'})
        format_cat2d_big = workbook.add_format({'bg_color':'#D9D9D9', 'num_format':'#,##0'})
        format_cat2d_lil = workbook.add_format({'bg_color':'#D9D9D9', 'num_format':'#,##0.000'})

        format_benval_lil = workbook.add_format({'num_format':'_($* #,##0.00_);_($* (#,##0.00);_($* "-"??_);_(@_)',
                                                'font_color':'#808080'})
        format_benval_big = workbook.add_format({'num_format':'_($* #,##0_);_($* (#,##0);_($* "-"??_);_(@_)',
                                                'font_color':'#808080'})
        format_ann_ben    = workbook.add_format({'num_format':'_($* #,##0_);_($* (#,##0);_($* "-"??_);_(@_)'})
        format_cat2_ben   = workbook.add_format({'num_format':'_($* #,##0_);_($* (#,##0);_($* "-"??_);_(@_)',
                                                 'bg_color':'#D9D9D9'})
        format_bc_header = workbook.add_format({'bg_color':'#92D050', 'align':'right','bold':True})
        format_bc_header_left = workbook.add_format({'bg_color':'#92D050', 'align':'left','bold':True})
        format_bc_header_center = workbook.add_format({'bg_color':'#92D050', 'align':'center','bold':True})

        format_bc_money = workbook.add_format({'bg_color':'#92D050','bold':True,
                                                'num_format':'_(\$* #,##0"M"_);_(\$* (#,##0"M");_(\$* "-"??_);_(@_)'})
        format_bc_ratio = workbook.add_format({'bg_color':'#92D050','bold':True,'num_format':'0.00'})

        format_equity = workbook.add_format({'bg_color':'#92D050', 'bold':True})
        format_equityscore = workbook.add_format({'bg_color':'#92D050','bold':True,'num_format':'0%'})
        format_equity_headers = workbook.add_format({'bg_color':'#D9D9D9', 'align':'left','bold':True})
        format_equity_headers_center = workbook.add_format({'bg_color':'#D9D9D9', 'align':'center','bold':True})
        #'bg_color':'#92D050'
        format_equitypop = workbook.add_format({'bg_color':'#D9D9D9','num_format':'_(* #,##0.0"M"_);_(* (#,##0.0"M");_(* "-"??_);_(@_)'})
        format_equityben = workbook.add_format({'bg_color':'#D9D9D9','num_format':'_($* #,##0.00_);_($* (#,##0.00);_($* "-"??_);_(@_)'})
        format_equitypct = workbook.add_format({'bg_color':'#92D050','bold':True, 'align':'center', 'num_format':'0%'})

        # for cat1 sums (total benefits for cat1)
        cat1_sums = collections.OrderedDict() # cell -> [cell1, cell2, cell3...]
        cat1_sumsPV1 = collections.OrderedDict() # cell -> [cell1, cell2, cell3...]
        cat1_sumsPV2 = collections.OrderedDict() # cell -> [cell1, cell2, cell3...]
        cat1_cell = None
        cat1_cellPV1 = None
        cat1_cellPV2 = None

        row_remember = row+1
        row_list = []

        for key,value in colA.daily_results.iteritems():

            # What's the valuation of this metric?
            valuation = None
            if (key[0],key[1],key[2]) in self.BENEFIT_VALUATION:
                valuation = self.BENEFIT_VALUATION[(key[0],key[1],key[2])][0]
            elif (key[0],key[1]) in self.BENEFIT_VALUATION:
                valuation = self.BENEFIT_VALUATION[(key[0],key[1])][0]
            elif (("for reference only" in key[0]) | ("Avg Minutes Active Transport per Person" in key[1]) | \
              ("Activity: Est Proportion Deaths Averted" in key[1])):
                None
            else:
                # these are purely informational
                print("Could not lookup benefit valuation for %s" % str(key))

            # is this already a diff (e.g. no diff)
            already_diff = False
            if (key[0],key[1],key[2]) in RunResults.ALREADY_DIFF:
                already_annual = RunResults.ALREADY_DIFF[(key[0],key[1],key[2])]
            elif (key[0],key[1]) in RunResults.ALREADY_DIFF:
                already_diff = RunResults.ALREADY_DIFF[(key[0],key[1])]

            # is this already annual?  (e.g. no daily -> annual transformation)
            already_annual = False
            if (key[0],key[1],key[2]) in RunResults.ALREADY_ANNUAL:
                already_annual = RunResults.ALREADY_ANNUAL[(key[0],key[1],key[2])]
            elif (key[0],key[1]) in RunResults.ALREADY_ANNUAL:
                already_annual = RunResults.ALREADY_ANNUAL[(key[0],key[1])]

            annualization = RunResults.ANNUALIZATION
            if (key[0],key[1],key[2]) in RunResults.ANNUALIZATION_FACTOR:
                annualization = RunResults.ANNUALIZATION_FACTOR[(key[0],key[1],key[2])]
            elif (key[0],key[1]) in RunResults.ANNUALIZATION_FACTOR:
                annualization = RunResults.ANNUALIZATION_FACTOR[(key[0],key[1])]

            # category one header
            if cat1 != key[0]:
                cat1 = key[0]
                worksheet.write(row,0,cat1,format_cat1)
                worksheet.write(row,1,"",format_cat1)
                if self.base_dir:

                    if (cat1_cell) and ("for reference only" not in cat1):
                        worksheet.write(cat1_cell,
                                        '=SUM(%s)/1000000' % str(',').join(cat1_sums[cat1_cell]),
                                        format_cat1_sum)
                    cat1_cell = xl_rowcol_to_cell(row,8)
                    cat1_sums[cat1_cell] = []

                    if (cat1_cellPV1) and ("for reference only" not in cat1):
                        worksheet.write(cat1_cellPV1,
                                        '=SUM(%s)/1000000' % str(',').join(cat1_sumsPV1[cat1_cellPV1]),
                                        format_cat1_sum)
                    cat1_cellPV1 = xl_rowcol_to_cell(row,10)
                    cat1_sumsPV1[cat1_cellPV1] = []

                    if (cat1_cellPV2) and ("for reference only" not in cat1):
                        worksheet.write(cat1_cellPV2,
                                        '=SUM(%s)/1000000' % str(',').join(cat1_sumsPV2[cat1_cellPV2]),
                                        format_cat1_sum)
                    cat1_cellPV2 = xl_rowcol_to_cell(row,12)
                    cat1_sumsPV2[cat1_cellPV2] = []

                    worksheet.write(row,2,"",format_cat1)
                    worksheet.write(row,3,"",format_cat1)
                    worksheet.write(row,4,"",format_cat1)
                    if ("for reference only" not in cat1):
                        worksheet.write(row,5,"",format_cat1)
                        worksheet.write(row,6,"",format_cat1)
                        worksheet.write(row,7,"",format_cat1)
                        worksheet.write(row,9,"",format_cat1)
                        worksheet.write(row,11,"",format_cat1)
                        cat1_cell_last       = cat1_cell
                        cat1_cellPV1_last    = cat1_cellPV1
                        cat1_cellPV2_last    = cat1_cellPV2
                row += 1

            # category two header
            if cat2 != key[1]:
                cat2 = key[1]
                worksheet.write(row,0,cat2,format_cat2)
                # Sum it
                if not already_diff:
                    worksheet.write(row,1,
                                    '=SUM(%s)' % xl_range(row+1,1,row+len(colA.daily_results[cat1][cat2]),1),
                                    format_cat2_lil if (cat1,cat2) in self.lil_cats else format_cat2_big)
                else:
                    worksheet.write(row,1,"",format_cat2)
                    worksheet.write(row,2,"",format_cat2)

                if self.base_dir:
                    if cat1 in colB.daily_results and cat2 in colB.daily_results[cat1]:
                        worksheet.write(row,2, # base
                                        '=SUM(%s)' % xl_range(row+1,2,row+len(colB.daily_results[cat1][cat2]),2),
                                        format_cat2b_lil if (cat1,cat2) in self.lil_cats else format_cat2b_big)

                    if already_annual and already_diff:
                        worksheet.write(row,3, # diff daily
                                        "",
                                        format_cat2d_lil if (cat1,cat2) in self.lil_cats else format_cat2d_big)
                        worksheet.write(row,4, # diff annual
                                        '=SUM(%s)' % xl_range(row+1,4,row+len(colA.daily_results[cat1][cat2]),4),
                                        format_cat2d_lil if (cat1,cat2) in self.lil_cats else format_cat2d_big)

                    elif already_annual and cat1 in colB.daily_results and cat2 in colB.daily_results[cat1]:
                        worksheet.write(row,3, # diff daily
                                        "",
                                        format_cat2d_lil if (cat1,cat2) in self.lil_cats else format_cat2d_big)
                        worksheet.write(row,4, # diff annual
                                        '=SUM(%s)' % xl_range(row+1,4,row+len(colA.daily_results[cat1][cat2]),4),
                                        format_cat2d_lil if (cat1,cat2) in self.lil_cats else format_cat2d_big)

                    else:
                        worksheet.write(row,3, # diff daily
                                        '=SUM(%s)' % xl_range(row+1,3,row+len(colA.daily_results[cat1][cat2]),3),
                                        format_cat2d_lil if (cat1,cat2) in self.lil_cats else format_cat2d_big)
                        worksheet.write(row,4, # diff annual
                                        '=SUM(%s)' % xl_range(row+1,4,row+len(colA.daily_results[cat1][cat2]),4),
                                        format_cat2d_lil if (cat1,cat2) in self.lil_cats else format_cat2d_big)

                    # worksheet.write(row,6, "", format_cat2d_lil)

                    if valuation != None:
                        worksheet.write(row,8,
                                        '=SUM(%s)' % xl_range(row+1,8,row+len(colA.daily_results[cat1][cat2]),8),
                                        format_cat2_ben)
                        worksheet.write(row,10,
                                        '=SUM(%s)' % xl_range(row+1,10,row+len(colA.daily_results[cat1][cat2]),10), # check this 10 at the end
                                        format_cat2_ben)
                        worksheet.write(row,12,
                                        '=SUM(%s)' % xl_range(row+1,12,row+len(colA.daily_results[cat1][cat2]),12),# check this 12 at the end
                                        format_cat2_ben)

                        cat1_sums[cat1_cell].append(xl_rowcol_to_cell(row,8))
                        cat1_sumsPV1[cat1_cellPV1].append(xl_rowcol_to_cell(row,10))
                        cat1_sumsPV2[cat1_cellPV2].append(xl_rowcol_to_cell(row,12))

                row += 1


            # details
            worksheet.write(row,0,key[2],format_var)

            if numpy.isnan(value):
                worksheet.write(row,1 if not already_diff else 3,"nan")
            else:
                worksheet.write(row,1 if not already_diff else 3,value,
                                format_val_lil if (cat1,cat2) in self.lil_cats else format_val_big)

            if already_annual and already_diff:
                bc_metrics[(cat1,cat2,key[2],'Annual Difference')] = value
                bc_metrics[(cat1,cat2,key[2],'Daily Difference')] = None
            elif already_diff:
                bc_metrics[(cat1,cat2,key[2],'Daily Difference')] = value
            else:
                bc_metrics[(cat1,cat2,key[2],colA_header)] = value

            if self.base_dir:

                if cat1 in colB.daily_results and cat2 in colB.daily_results[cat1]:
                    worksheet.write(row,2, # base
                                    colB.daily_results[cat1][cat2][key[2]],
                                    format_val_lil if (cat1,cat2) in self.lil_cats else format_val_big)
                    nominal_diff = 0
                    bc_metrics[(cat1,cat2,key[2],colB_header)] = colB.daily_results[cat1][cat2][key[2]]


                if already_annual and already_diff:
                    worksheet.write(row,4, value, format_val_lil if (cat1,cat2) in self.lil_cats else format_val_big) # diff annual
                    nominal_diff =  value
                    bc_metrics[(cat1,cat2,key[2],'Annual Difference')] = nominal_diff

                elif already_annual and not already_diff:
                    worksheet.write(row,4, # diff annual
                                    '=%s-%s' % (xl_rowcol_to_cell(row,1), xl_rowcol_to_cell(row,2)),
                                    format_val_lil if (cat1,cat2) in self.lil_cats else format_val_big)
                    nominal_diff = colA.daily_results[cat1][cat2][key[2]] - \
                                   colB.daily_results[cat1][cat2][key[2]]
                    bc_metrics[(cat1,cat2,key[2],'Annual Difference')] = nominal_diff

                else:
                    if not already_diff:
                        worksheet.write(row,3, # diff daily
                                        '=%s-%s' % (xl_rowcol_to_cell(row,1), xl_rowcol_to_cell(row,2)),
                                        format_val_lil if (cat1,cat2) in self.lil_cats else format_val_big)
                        bc_metrics[(cat1,cat2,key[2],'Daily Difference')] = colA.daily_results[cat1][cat2][key[2]] - \
                                                                            colB.daily_results[cat1][cat2][key[2]]
                        if colB.daily_results[cat1][cat2][key[2]] != 0:
                            bc_metrics[(cat1,cat2,key[2],'Daily Percent Difference')] = bc_metrics[(cat1,cat2,key[2],'Daily Difference')] / \
                                                                            colB.daily_results[cat1][cat2][key[2]]
                        else:
                            bc_metrics[(cat1,cat2,key[2],'Daily Percent Difference')] = 0

                    worksheet.write(row,4, # diff annual
                                    '=%d*%s' % (annualization, xl_rowcol_to_cell(row,3)),
                                    format_val_lil if (cat1,cat2) in self.lil_cats else format_val_big)
                    bc_metrics[(cat1,cat2,key[2],'Annual Difference')] = annualization*bc_metrics[(cat1,cat2,key[2],'Daily Difference')]

                    if already_diff:
                        nominal_diff = annualization * colA.daily_results[cat1][cat2][key[2]]
                    else:
                        nominal_diff = annualization * (colA.daily_results[cat1][cat2][key[2]] - \
                                                        colB.daily_results[cat1][cat2][key[2]])

                # Multiplying annual nominal difference * valuation = Annual Benefit
                if valuation != None:
                    worksheet.write(row,6, # valuation
                                    valuation,
                                    format_benval_lil if abs(valuation)<1000 else format_benval_big)
                    worksheet.write(row,8, # annual benefit
                                    '=%s*%s' % (xl_rowcol_to_cell(row,4), xl_rowcol_to_cell(row,6)),
                                    format_ann_ben)
                    row_list.append(row)
                    bc_metrics[(cat1,cat2,key[2],'Horizon Yr Benefit (2019$)')] = valuation*nominal_diff

            row += 1



        #add proxies as a worksheet
        if self.base_dir:
            self.writeProxiesWorksheet(workbook)


        #*****************************************************************************************
        #calculate cost streams in a separate worksheet
        if self.base_dir:
            imp_years = self.writeCostsWorksheet(workbook, bc_metrics, scen_minus_baseline=False)


        #*****************************************************************************************
        #calculate benefit streams in a separate worksheet
        if self.base_dir:
            if self.config.loc['Compare'] == 'scenario-baseline':
                bc_metrics_annual_benefit = self.writeBenefitStreamsWorksheet(workbook, bc_metrics, imp_years)
            else:
                bc_metrics_annual_benefit = self.writeBenefitStreamsWorksheet(workbook, bc_metrics, imp_years, scen_minus_baseline=False)


        # insert present values of benefits for each benefit item from the newly created streams worksheet
        row = row_remember -1
        for key,value in colA.daily_results.iteritems():

            if cat1 != key[0]:
                cat1 = key[0]
                row += 1
            if cat2 != key[1]:
                cat2 = key[1]
                row += 1

            if self.base_dir:
                if "for reference only" not in key[0]:
                    if ((key[0],key[1]) in self.BENEFIT_VALUATION) or ((key[0],key[1],key[2]) in self.BENEFIT_VALUATION) :
                        worksheet.write(row,10, # PV 2025-2060
                                        '=benefit_streams!%s' %bc_metrics_annual_benefit.get([(key[0],key[1],key[2],'NPV2025-60cell')][0]),
                                        format_ann_ben)
                        worksheet.write(row,12, # PV 2025-2080
                                        '=benefit_streams!%s' %bc_metrics_annual_benefit.get([(key[0],key[1],key[2],'NPV2025-80cell')][0]),
                                        format_ann_ben)
            row+=1


        # Equity Score
        if self.base_dir:
            population_lowinc = self.accessibilityMarkets.loc[self.accessibilityMarkets['incQ_label'] == "lowInc", 'scen_num_persons'].sum()
            population_medinc = self.accessibilityMarkets.loc[self.accessibilityMarkets['incQ_label'] == "medInc", 'scen_num_persons'].sum()
            population_highinc = self.accessibilityMarkets.loc[self.accessibilityMarkets['incQ_label'] == "highInc", 'scen_num_persons'].sum()
            population_veryhighinc = self.accessibilityMarkets.loc[self.accessibilityMarkets['incQ_label'] == "veryHighInc", 'scen_num_persons'].sum()
            population_total = self.accessibilityMarkets['scen_num_persons'].sum()
            pct_lowinc = float(population_lowinc) / population_total
            pct_medinc = float(population_lowinc+population_medinc) / population_total

            worksheet.write(TABLE_HEADER_ROW-4,0, "Equity Score Calculation", format_equity_headers)
            worksheet.write(TABLE_HEADER_ROW-3,0, "Total Population", format_equity_headers)
            worksheet.write(TABLE_HEADER_ROW-2,0, "Avg Accessibility Benefit per Individual", format_equity_headers)

            worksheet.write(TABLE_HEADER_ROW-4,1, "LowInc", format_equity_headers_center)
            worksheet.write(TABLE_HEADER_ROW-4,2, "MedInc", format_equity_headers_center)
            worksheet.write(TABLE_HEADER_ROW-4,3, "HighInc", format_equity_headers_center)
            worksheet.write(TABLE_HEADER_ROW-4,4, "VeryHighInc", format_equity_headers_center)

            worksheet.write(TABLE_HEADER_ROW-3,1, float(population_lowinc)/1000000, format_equitypop)
            worksheet.write(TABLE_HEADER_ROW-3,2, float(population_medinc)/1000000, format_equitypop)
            worksheet.write(TABLE_HEADER_ROW-3,3, float(population_highinc)/1000000, format_equitypop)
            worksheet.write(TABLE_HEADER_ROW-3,4, float(population_veryhighinc)/1000000, format_equitypop)

            worksheet.write(TABLE_HEADER_ROW-2,1, '=(I19+I24) / (%s*1000000)' %xl_rowcol_to_cell(TABLE_HEADER_ROW-3, 1), format_equityben)
            worksheet.write(TABLE_HEADER_ROW-2,2, '=(I20+I25) / (%s*1000000)' %xl_rowcol_to_cell(TABLE_HEADER_ROW-3, 2), format_equityben)
            worksheet.write(TABLE_HEADER_ROW-2,3, '=(I21+I26) / (%s*1000000)' %xl_rowcol_to_cell(TABLE_HEADER_ROW-3, 3), format_equityben)
            worksheet.write(TABLE_HEADER_ROW-2,4, '=(I22+I27) / (%s*1000000)' %xl_rowcol_to_cell(TABLE_HEADER_ROW-3, 4), format_equityben)

            worksheet.write(TABLE_HEADER_ROW-5,0, 'Equity Score', format_bc_header_left)
            worksheet.write(TABLE_HEADER_ROW-5,1, '=(%s+%s)/sum(%s:%s)'%(xl_rowcol_to_cell(TABLE_HEADER_ROW-2, 1),\
                                                                          xl_rowcol_to_cell(TABLE_HEADER_ROW-2, 2),\
                                                                          xl_rowcol_to_cell(TABLE_HEADER_ROW-2, 1),\
                                                                          xl_rowcol_to_cell(TABLE_HEADER_ROW-2, 4)), format_equitypct)

        # Summing up for total benefits

        if self.base_dir:

            # Calculate the last cat1 sum
            if cat1_cell_last:
                worksheet.write(cat1_cell_last,
                                '=SUM(%s)/1000000' % str(',').join(cat1_sums[cat1_cell_last]),
                                format_cat1_sum)
            if cat1_cellPV1_last:
                worksheet.write(cat1_cellPV1_last,
                                '=SUM(%s)/1000000' % str(',').join(cat1_sumsPV1[cat1_cellPV1_last]),
                                format_cat1_sum)
            if cat1_cellPV2_last:
                worksheet.write(cat1_cellPV2_last,
                                '=SUM(%s)/1000000' % str(',').join(cat1_sumsPV2[cat1_cellPV2_last]),
                                format_cat1_sum)


            # BENEFIT/COST
            # labels
            worksheet.write(TABLE_HEADER_ROW-4, 6, "Benefit"  ,format_bc_header)
            worksheet.write(TABLE_HEADER_ROW-3, 6, "Cost"     ,format_bc_header)
            worksheet.write(TABLE_HEADER_ROW-2, 6, "B/C Ratio",format_bc_header)

            # space
            worksheet.write(TABLE_HEADER_ROW-4, 7, "",format_bc_header)
            worksheet.write(TABLE_HEADER_ROW-3, 7, "",format_bc_header)
            worksheet.write(TABLE_HEADER_ROW-2, 7, "",format_bc_header)

            sum_indices = cat1_sums.keys()
            sum_indices_PV1 = cat1_sumsPV1.keys()
            sum_indices_PV2 = cat1_sumsPV2.keys()

            # choose the correct major categories for summing; drop 1,3,4 = logsum no cem, travel time, travel cost
            sum_indices = [sum_indices[0]] + sum_indices[2:7]
            sum_indices_PV1 = [sum_indices_PV1[0]] + sum_indices_PV1[2:7]
            sum_indices_PV2 = [sum_indices_PV2[0]] + sum_indices_PV2[2:7]

            worksheet.write(TABLE_HEADER_ROW-5, 8, 'Horizon Year', format_bc_header_left)
            worksheet.write(TABLE_HEADER_ROW-5, 10, 'NPV 2025-60', format_bc_header_left)
            worksheet.write(TABLE_HEADER_ROW-5, 12, 'NPV 2025-80', format_bc_header_left)

            # summing major benefit categories
            worksheet.write(TABLE_HEADER_ROW-4, 8, "=SUM(%s)" % str(",").join(sum_indices), format_bc_money)
            worksheet.write(TABLE_HEADER_ROW-4, 10, "=SUM(%s)" % str(",").join(sum_indices_PV1), format_bc_money)
            worksheet.write(TABLE_HEADER_ROW-4, 12, "=SUM(%s)" % str(",").join(sum_indices_PV2), format_bc_money)

            # getting costs
            worksheet.write(TABLE_HEADER_ROW-3, 8, "=cost_streams!E2/1000000", format_bc_money)
            worksheet.write(TABLE_HEADER_ROW-3, 10, "=cost_streams!F2/1000000", format_bc_money)
            worksheet.write(TABLE_HEADER_ROW-3, 12, "=cost_streams!G2/1000000", format_bc_money)


            # calculating b/c ratio
            for col in [8,10,12]:
                worksheet.write(TABLE_HEADER_ROW-2, col, "=%s/%s" % (xl_rowcol_to_cell(TABLE_HEADER_ROW-4, col),
                                                                    xl_rowcol_to_cell(TABLE_HEADER_ROW-3, col)), format_bc_ratio)

        worksheet.set_column(0,0,40.0)
        worksheet.set_column(1,8,13.0)
        worksheet.set_column(5,5,2.0)
        worksheet.set_column(7,7,2.0)
        worksheet.set_column(9,9,2.0)
        worksheet.set_column(11,11,2.0)

        worksheet.set_column(8,8,15.0)
        worksheet.set_column(10,10,18.0)
        worksheet.set_column(12,12,18.0)

        # THIS IS COBRA
        format_red      = workbook.add_format({'font_color':'white','bg_color':'#C0504D','align':'right','bold':True})
        for row in range(2,10):
            for col in range(9,13):
                worksheet.write(row,col,"",format_red)
        worksheet.write(4,11,"co",format_red)
        worksheet.write(5,11,"b" ,format_red)
        worksheet.write(6,11,"r" ,format_red)
        worksheet.write(7,11,"a" ,format_red)
        format_red      = workbook.add_format({'font_color':'white','bg_color':'#C0504D'})
        worksheet.write(4,12,"st",format_red)
        worksheet.write(5,12,"enefit" ,format_red)
        worksheet.write(6,12,"results" ,format_red)
        worksheet.write(7,12,"nalyzer" ,format_red)


        worksheet.insert_image(3, 10,
                               os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "King-cobra.png"),
                               {'x_scale':0.1, 'y_scale':0.1})
        return bc_metrics


    def writeProxiesWorksheet(self, workbook):

        # Reading proxies from master input file
        df_proxies = pd.read_excel(self.ppa_master_input, sheet_name='stream_proxies', header=0)
        df_proxies = df_proxies.loc[df_proxies['Future']==self.config.loc['Future']]
        df_proxies = df_proxies.loc[(df_proxies['Project Type']==self.config.loc['Project Type']) | (df_proxies['Project Type']=="All")]
        df_proxies = df_proxies.drop(['Future', 'Project Type', 'Base2015', 'Base2030', 'Base2050'], axis=1)

        format_basicstats = workbook.add_format({'bg_color':'#FFFFC0', 'bold':True})
        format_header = workbook.add_format({'bg_color':'#1F497D',
                                             'font_color':'white',
                                             'bold':True,
                                             'text_wrap':True,
                                             'align':'center'})
        format_bold = workbook.add_format({'bold':True, 'num_format':'#,##0.00'})
        format_value  = workbook.add_format({'num_format':'#,##0.00'})

        # create worksheet for proxies
        worksheet=None
        if self.base_dir:
            try:
                worksheet = workbook.add_worksheet('proxies')
            except:
                return []
        else:
            return
        worksheet.protect()

        row = 0
        # basic stats about project
        worksheet.write(row,0,'This sheet represents the proxies obtained from baseline no-project scenarios and is used to extrapolate project benefit streams. These proxies are for:', format_basicstats)
        for col in range(1,8):
            worksheet.write(row,col,'',format_basicstats)
        row+=1

        worksheet.write(row,0,'Future', format_basicstats)
        worksheet.write(row,1, self.config.loc['Future'], format_basicstats)
        row+=1
        worksheet.write(row,0,'Project Type', format_basicstats)
        worksheet.write(row,1, self.config.loc['Project Type'], format_basicstats)

        writer = pd.ExcelWriter(workbook, engine = 'xlsxwriter')
        writer.sheets['proxies'] = worksheet
        df_proxies.to_excel(writer, sheet_name = 'proxies', startrow=4, index=False)

        for col_num, value in enumerate(df_proxies.columns.values):
            worksheet.write(4, col_num, value, format_header)


        worksheet.set_column(3,69,None,format_value)
        worksheet.set_column(0,2,30.0)
        worksheet.set_column(6,6,10.0)
        worksheet.set_column(3,3,None,format_bold)
        worksheet.set_column(8,8,None,format_bold)
        worksheet.set_column(18,18,None,format_bold)
        worksheet.set_column(28,28,None,format_bold)
        worksheet.set_column(38,38,None,format_bold)
        worksheet.set_column(48,48,None,format_bold)
        worksheet.set_column(58,58,None,format_bold)
        worksheet.set_column(68,68,None,format_bold)
        worksheet.freeze_panes(5,3)

        print("Wrote the proxies worksheet")
        return


    def writeBenefitStreamsWorksheet(self, workbook, bc_metrics, imp_years, scen_minus_baseline=True):
        """
        Writes the proxies into the workbook, reading from a reference file.
        Writes another worksheet into the workbook, to calculate the benefits streams and their present values
        """
        format_header = workbook.add_format({'bg_color':'#1F497D',
                                             'font_color':'white',
                                             'bold':True,
                                             'text_wrap':True,
                                             'align':'center'})
        format_basicstats = workbook.add_format({'bg_color':'#FFFFC0', 'bold':True})
        format_ann_ben  = workbook.add_format({'num_format':'_($* #,##0_);_($* (#,##0);_($* "-"??_);_(@_)'})
        format_2060 = workbook.add_format({'num_format':'_($* #,##0_);_($* (#,##0);_($* "-"??_);_(@_)', 'bg_color':'#D9D9D9', 'bold':True})
        format_npv   = workbook.add_format({'num_format':'_($* #,##0_);_($* (#,##0);_($* "-"??_);_(@_)',
                                                 'bg_color':'#C5D9F1', 'bold':True})

        # create worksheet for streams
        worksheet=None
        try:
            worksheet = workbook.add_worksheet('benefit_streams')
        except:
            worksheet = workbook.add_worksheet('benefit_streams1')
        worksheet.protect()


        # basic stats about project
        row = 0
        worksheet.write(row,0,'This sheet forecasts benefit streams based on the Horizon Year 2050 value output by the model, and proxies at every 10 year interval sourced from intermediate year model runs for no-project scenario', format_basicstats)
        for col in range(1,8):
            worksheet.write(row,col,'',format_basicstats)
        row+=1
        worksheet.write(row,0,'Discount rate', format_basicstats)
        worksheet.write(row,1, RunResults.DISCOUNT_RATE, format_basicstats)
        DISCOUNT_RATE_ROW = row
        row+=1
        worksheet.write(row,0,'All costs are in 2019$', format_basicstats)
        row+=2


        # insert column headers
        worksheet.write(row,0,'Benefit Category 1',format_header)
        worksheet.write(row,1,'Benefit Category 2',format_header)
        worksheet.write(row,2,'Benefit Category 3',format_header)
        worksheet.write(row,3,'Horizon Yr Benefit\n2050\n(2019$)',format_header)
        worksheet.write(row,4,'Benefits NPV\n2025-60\n(2019$)',format_header)
        worksheet.write(row,5,'Benefits NPV\n2025-80\n(2019$)',format_header)
        for col in range(6,62):
            worksheet.write(row,col,'Benefit\n%d\n(2019$)'%(2019+col),format_header)
        TABLE_HEADER_ROW = row
        row+=1


        bc_metrics_annual_benefit = collections.OrderedDict()
        for key,val in bc_metrics.iteritems():
            if "for reference only" not in key[0]:
                if key[3]=='Horizon Yr Benefit (2019$)':
                    bc_metrics_annual_benefit[key] = val

        bc_metrics_withNPV = collections.OrderedDict()

        for key,val in bc_metrics_annual_benefit.iteritems():

            # insert first few columns as categories and labels from bc_metrics
            worksheet.write(row, 0, key[0])
            worksheet.write(row, 1, key[1])
            worksheet.write(row, 2, key[2])
            worksheet.write(row, 3, val, format_2060)
            #formulas to calculate present values of each benefit
            worksheet.write(row, 4, '=NPV(%s,%s:%s)' %(xl_rowcol_to_cell(DISCOUNT_RATE_ROW,1), xl_rowcol_to_cell(row,6), xl_rowcol_to_cell(row,41)), format_npv)
            worksheet.write(row, 5, '=NPV(%s,%s:%s)' %(xl_rowcol_to_cell(DISCOUNT_RATE_ROW,1), xl_rowcol_to_cell(row,6), xl_rowcol_to_cell(row,61)), format_npv)

            #remembering the cell location of the NPV for each benefit item
            bc_metrics_withNPV[(key[0],key[1],key[2],'NPV2025-60cell')] = xl_rowcol_to_cell(row,4)
            bc_metrics_withNPV[(key[0],key[1],key[2],'NPV2025-80cell')] = xl_rowcol_to_cell(row,5)

            col = 6
            while col<(6+imp_years):            # zero benefit until project is implemented
                worksheet.write(row, col, 0, format_ann_ben)
                col = col+1

            col = 6 + imp_years
            while col<=61:     #multiplying annual horizon year benefit times proxies from year 2025-2080
                worksheet.write(row, col, '=%s*proxies!%s' % (xl_rowcol_to_cell(row,3), xl_rowcol_to_cell(row,col+7)), \
                  format_2060 if (col in [41,61]) else format_ann_ben)
                col = col+1
            row+=1


        worksheet.set_column(0,2,30.0)
        worksheet.set_column(3,5,20.0)
        worksheet.set_column(6,6,10.0)
        worksheet.set_column(7,61,15.0)
        worksheet.freeze_panes(5,3)

        print("Wrote the benefit streams worksheet")
        return bc_metrics_withNPV


    def writeCostsWorksheet(self, workbook, bc_metrics, scen_minus_baseline=True):
        """
        Writes the costs into the workbook
        Writes another worksheet into the workbook, to calculate the benefits streams and their present values
        """
        format_header = workbook.add_format({'bg_color':'#1F497D',
                                             'font_color':'white',
                                             'bold':True,
                                             'text_wrap':True,
                                             'align':'center'})
        format_ann_ben    = workbook.add_format({'num_format':'_($* #,##0_);_($* (#,##0);_($* "-"??_);_(@_)'})
        format_totals   = workbook.add_format({'num_format':'_($* #,##0_);_($* (#,##0);_($* "-"??_);_(@_)','bg_color':'#C5D9F1', 'bold':True})
        format_na = workbook.add_format({'align': 'right'})
        format_input = workbook.add_format({'num_format':'_($* #,##0_);_($* (#,##0);_($* "-"??_);_(@_)'})
        format_costs = workbook.add_format({'num_format':'_($* #,##0_);_($* (#,##0);_($* "-"??_);_(@_)'})
        format_2060   = workbook.add_format({'num_format':'_($* #,##0_);_($* (#,##0);_($* "-"??_);_(@_)', 'bg_color':'#D9D9D9', 'bold':True})
        format_remainder   = workbook.add_format({'num_format':'_($* #,##0_);_($* (#,##0);_($* "-"??_);_(@_)', 'bg_color':'#D9D9D9', 'bold':True})
        format_basicstats = workbook.add_format({'bg_color':'#FFFFC0', 'bold':True})
        format_total_num = workbook.add_format({'bg_color':'#92D050','bold':True, 'num_format':'_($* #,##0_);_($* (#,##0);_($* "-"??_);_(@_)'})
        format_total_num_M = workbook.add_format({'bg_color':'#92D050','bold':True, 'num_format':'_(\$* #,##0"M"_);_(\$* (#,##0"M");_(\$* "-"??_);_(@_)'})
        format_total = workbook.add_format({'bg_color':'#92D050','bold':True})

        # create worksheet for streams
        worksheet=None
        try:
            worksheet = workbook.add_worksheet('cost_streams')
        except:
            worksheet = workbook.add_worksheet('cost_streams1')
        worksheet.protect()
        row=0


        # basic stats about project
        imp_years = self.proj_costs.get('Years required to implement')
        worksheet.write(row,0,'Years required to implement', format_basicstats)
        worksheet.write(row,1, imp_years, format_basicstats)
        IMP_YEAR_ROW = row
        row+=1
        worksheet.write(row,0,'Discount rate', format_basicstats)
        worksheet.write(row,1, RunResults.DISCOUNT_RATE, format_basicstats)
        DISCOUNT_RATE_ROW = row
        row+=1
        worksheet.write(row,0,'All costs are in 2019$', format_basicstats)



        # insert column headers
        row+=2
        TABLE_HEADER_ROW = row
        worksheet.write(row,0,'Cost Bucket',format_header)
        worksheet.write(row,1,'Cost Category',format_header)
        worksheet.write(row,2,'Asset Life\n(if applicable)',format_header)
        worksheet.write(row,3,'Cost Input',format_header)
        worksheet.write(row,4,'Annualized Cost\n(PBA40 method)\n(2019$)',format_header)
        worksheet.write(row,5,'Costs NPV\n2025-60\n(2019$)',format_header)
        worksheet.write(row,6,'Costs NPV\n2025-80\n(2019$)',format_header)
        for col in range(7,63):
            worksheet.write(row,col,'Cost\n%d\n(2019$)'%(2018+col),format_header)
        worksheet.write(row,63,'Remaining Value\nas of 2060 (2019$)',format_header)
        worksheet.write(row,64,'Remaining Value\nas of 2080 (2019$)',format_header)


        worksheet.set_column(0,1,20.0)
        worksheet.set_column(2,2,10.0)
        worksheet.set_column(3,6,20.0)
        worksheet.set_column(7,62,15.0)
        worksheet.set_column(63,64,20.0)


        # Capital and O&M cost rows

        row+=1
        for key,val in self.proj_costs.iteritems():
            if key in self.asset_life.keys():     # if key is a capital cost
                asset_life_value = self.asset_life.get(key)
                worksheet.write(row, 0, "Capital Cost")
                worksheet.write(row, 1, key)                   # asset category
                worksheet.write(row, 2, asset_life_value)      # asset life
                worksheet.write(row, 3, val, format_input)     # cost input
                worksheet.write(row, 4, '=%s/%s' %(xl_rowcol_to_cell(row,3), (xl_rowcol_to_cell(row,2))), format_remainder)
                i=7
                while i<(7+imp_years):
                    worksheet.write(row, i, '=%s/%s' %(xl_rowcol_to_cell(row,3), xl_rowcol_to_cell(IMP_YEAR_ROW,1)), format_2060 if (i in [42,62]) else format_costs)
                    i+=1
                while i<=62:                                                 # filling in empty cells with 0
                    worksheet.write(row, i, 0, format_2060 if (i in [42,62]) else format_costs)
                    i+=1
                row+=1
            elif key=="O&M Cost (annual 2019$)":                              # if key is operating cost
                worksheet.write(row, 0, "O&M Cost (annual)")
                worksheet.write(row, 1, "n/a")
                worksheet.write(row, 2, "n/a", format_na)
                worksheet.write(row, 3, val, format_input)                    # cost input
                worksheet.write(row, 4, '=%s' %(xl_rowcol_to_cell(row,3)), format_remainder)
                i=7
                while i<(7+imp_years):                                        # filling in empty cells with 0
                    worksheet.write(row, i, 0, format_2060 if (i in [42,62]) else format_costs)
                    i+=1
                for j in range(i,63):
                    worksheet.write(row, j, '=%s' %(xl_rowcol_to_cell(row,3)), format_2060 if (j in [42,62]) else format_costs)
                row+=1
            else:
                pass
            worksheet.write(row, 63, 0, format_remainder)
            worksheet.write(row, 64, 0, format_remainder)



        # Rehab and Replacement costs; Remaining asset value

        for key,val in self.proj_costs.iteritems():

            if key == "Road - Pavement":
                worksheet.write(row, 0, "Rehab Cost")
                worksheet.write(row, 1, key)                   # asset category
                worksheet.write(row, 2, "n/a", format_na)
                worksheet.write(row, 3, val, format_input)                   # cost input
                worksheet.write(row, 4, 0, format_remainder)
                i=7
                while i<(7+imp_years+4):                        # filling in empty cells with 0
                    worksheet.write(row, i, 0, format_2060 if (i in [42,62]) else format_costs)
                    i+=1
                i = 7 + imp_years + 4           # Rehab costs: 10% of initial investment cost at year 5
                j=1                             #              20% of initial investment cost at year 10
                while i<=62:                     #              30% of initial investment cost at year 20
                    if j==1:
                        worksheet.write(row, i, '=%s*0.1' %(xl_rowcol_to_cell(row,3)), format_2060 if (i in [42,62]) else format_costs)
                        col=i+1
                        while col<(i+5) and col<=62:            # filling in empty cells with 0
                            worksheet.write(row, col, 0, format_2060 if (col in [42,62]) else format_costs)
                            col+=1
                        j=2
                        i+=5
                    elif j==2:
                        worksheet.write(row, i, '=%s*0.2' %(xl_rowcol_to_cell(row,3)), format_2060 if (i in [42,62]) else format_costs)
                        col=i+1
                        while col<(i+10) and col<=62:           # filling in empty cells with 0
                            worksheet.write(row, col, 0, format_2060 if (col in [42,62]) else format_costs)
                            col+=1
                        j=3
                        i+=10
                    elif j==3:
                        worksheet.write(row, i, '=%s*0.3' %(xl_rowcol_to_cell(row,3)), format_2060 if (i in [42,62]) else format_costs)
                        col=i+1
                        while col<(i+5) and col<=62:            # filling in empty cells with 0
                            worksheet.write(row, col, 0, format_2060 if (col in [42,62]) else format_costs)
                            col+=1
                        j=1
                        i+=5
                # Remaining asset value: initial cost*(1 - (avg annual rehab / discount rate))
                # note: avg annual rehab when accounting for the rehab payment schedule is ~ 2.6% of initial investment cost
                worksheet.write(row, 63, '=%s - (0.026*%s/%s)' %(xl_rowcol_to_cell(row,3), xl_rowcol_to_cell(row,3), xl_rowcol_to_cell(1,1)), format_remainder)
                worksheet.write(row, 64, '=%s - (0.026*%s/%s)' %(xl_rowcol_to_cell(row,3), xl_rowcol_to_cell(row,3), xl_rowcol_to_cell(1,1)), format_remainder)
                row+=1

            elif key == "Road - Structures":
                worksheet.write(row, 0, "Rehab Cost")
                worksheet.write(row, 1, key)                   # asset category
                worksheet.write(row, 2, "n/a", format_na)
                worksheet.write(row, 3, val, format_input)                   # cost input
                worksheet.write(row, 4, 0, format_remainder)
                i=7
                while i<(7+imp_years+4):                        # filling in empty cells with 0
                    worksheet.write(row, i, 0, format_2060 if (i in [42,62]) else format_costs)
                    i+=1
                i = 7 + imp_years + 4           # Rehab costs: 20% of initial investment cost at year 5
                j=1                             #              20% of initial investment cost at year 15
                while i<=62:                     #              30% of initial investment cost at year 35
                    if j==1:
                        worksheet.write(row, i, '=%s*0.2' %(xl_rowcol_to_cell(row,3)), format_2060 if (i in [42,62])  else format_costs)
                        col=i+1
                        while col<(i+10) and col<=62:         # filling in empty cells with 0
                            worksheet.write(row, col, 0, format_2060 if (col in [42,62]) else format_costs)
                            col+=1
                        j=2
                        i+=10
                    elif j==2:
                        worksheet.write(row, i, '=%s*0.2' %(xl_rowcol_to_cell(row,3)), format_2060 if (i in [42,62]) else format_costs)
                        col=i+1
                        while col<(i+20) and col<=62:          # filling in empty cells with 0
                            worksheet.write(row, col, 0, format_2060 if (col in [42,62]) else format_costs)
                            col+=1
                        j=3
                        i+=20
                    elif j==3:
                        worksheet.write(row, i, '=%s*0.3' %(xl_rowcol_to_cell(row,3)), format_2060 if (i in [42,62]) else format_costs)
                        col=i+1
                        while col<(i+5) and col<=62:            # filling in empty cells with 0
                            worksheet.write(row, col, 0, format_2060 if (col in [42,62]) else format_costs)
                            col+=1
                        j=1
                        i+=5
                # Remaining asset value: initial cost - (avg annual rehab / discount rate)
                # note: avg annual rehab when accounting for the rehab payment schedule is ~ 1.9% of initial investment cost
                worksheet.write(row, 63, '=%s - (0.019*%s/%s)' %(xl_rowcol_to_cell(row,3), xl_rowcol_to_cell(row,3), xl_rowcol_to_cell(1,1)), format_remainder)
                worksheet.write(row, 64, '=%s - (0.019*%s/%s)' %(xl_rowcol_to_cell(row,3), xl_rowcol_to_cell(row,3), xl_rowcol_to_cell(1,1)), format_remainder)
                row+=1


            elif key in self.asset_life.keys():                             # if key is Capital costs apart from Road pavement
                asset_life_value = self.asset_life.get(key)
                worksheet.write(row, 0, "Replacement Cost")
                worksheet.write(row, 1, key)                                 # asset category
                worksheet.write(row, 2, asset_life_value)                    # asset life
                worksheet.write(row, 3, val, format_input)                   # cost input
                worksheet.write(row, 4, 0, format_remainder)
                i=7
                while i<(7 + imp_years + asset_life_value - 1) and i<=62:              # filling in empty cells with 0
                    worksheet.write(row, i, 0, format_2060 if (i in [42,62]) else format_costs)
                    i+=1
                #if key == "Soft Costs":                                     # note: this is done for Soft Costs since asset life is 0
                #    worksheet.write(row, 63, 0, format_remainder)
                #    worksheet.write(row, 64, 0, format_remainder)

                col_2080 = 7 + imp_years + asset_life_value - 1              # Replacement cost = initial cost every turnover of asset life
                col_2060 = col_2080
                i=0
                while col_2080<=62:                                           # calculating replacement costs until 2080
                    worksheet.write(row, col_2080, '=%s' %(xl_rowcol_to_cell(row,3)), format_2060 if (col_2080 in [42,62]) else format_costs)
                    col=col_2080+1
                    while col<(col_2080+asset_life_value) and col<=62:            # filling in empty cells with 0
                        worksheet.write(row, col, 0, format_2060 if (col in [42,62]) else format_costs)
                        col+=1
                    col_2080+=asset_life_value
                    i=1
                while col_2060<=42:                                           # to be able to calculate remaining asset value at 2060
                    col_2060+=asset_life_value
                # Remaining asset value: initial cost * (1 - (years of life remaining/asset life))
                worksheet.write(row, 63, '=%s * %i/%s' %(xl_rowcol_to_cell(row,3), col_2060-42, xl_rowcol_to_cell(row,2)), format_remainder)
                worksheet.write(row, 64, '=%s * %i/%s' %(xl_rowcol_to_cell(row,3), col_2080-62, xl_rowcol_to_cell(row,2)), format_remainder)

                row+=1

            else:
                pass




        # Residual value row - the last row
        worksheet.write(row, 0, "Residual Value")
        worksheet.write(row, 1, "n/a")
        worksheet.write(row, 2, "n/a", format_na)
        worksheet.write(row, 3, 0, format_input)
        worksheet.write(row, 4, 0, format_remainder)
        worksheet.write(row, 63, '=sum(%s:%s)' %(xl_rowcol_to_cell(TABLE_HEADER_ROW+1,63), xl_rowcol_to_cell(row-1,63)), format_remainder)
        worksheet.write(row, 64, '=sum(%s:%s)' %(xl_rowcol_to_cell(TABLE_HEADER_ROW+1,64), xl_rowcol_to_cell(row-1,64)), format_remainder)
        row+=1


        # Calculating NPVs for each cost line
        for row_num in range(TABLE_HEADER_ROW+1,row-1):
            worksheet.write(row_num, 5, '=NPV(%s,%s:%s)' %(xl_rowcol_to_cell(DISCOUNT_RATE_ROW,1), xl_rowcol_to_cell(row_num,7), xl_rowcol_to_cell(row_num,42)), format_totals)
            worksheet.write(row_num, 6, '=NPV(%s,%s:%s)' %(xl_rowcol_to_cell(DISCOUNT_RATE_ROW,1), xl_rowcol_to_cell(row_num,7), xl_rowcol_to_cell(row_num,62)), format_totals)
        worksheet.write(row-1, 5, '=%s/((1+%s)^35)' %(xl_rowcol_to_cell(row-1,63), xl_rowcol_to_cell(DISCOUNT_RATE_ROW,1)), format_totals)
        worksheet.write(row-1, 6, '=%s/((1+%s)^55)' %(xl_rowcol_to_cell(row-1,64), xl_rowcol_to_cell(DISCOUNT_RATE_ROW,1)), format_totals)


        # Calculating total costs


        worksheet.write(0, 4, 'Annualized', format_total)
        worksheet.write(0, 5, 'PV (2025-60)', format_total)
        worksheet.write(0, 6, 'PV (2025-80)', format_total)
        worksheet.write(1, 3, 'Total Cost (2019$)', format_total)
        worksheet.write(2, 3, 'Initial Capital Cost (2019$)', format_total)
        worksheet.write(3, 3, 'O&M (2019$)', format_total)

        # Total cost
        worksheet.write(1, 4, '=sum(%s:%s) - %s' %(xl_rowcol_to_cell(TABLE_HEADER_ROW+1,4), xl_rowcol_to_cell(row-2,4), xl_rowcol_to_cell(row-1,4)), format_total_num)
        worksheet.write(1, 5, '=sum(%s:%s) - %s' %(xl_rowcol_to_cell(TABLE_HEADER_ROW+1,5), xl_rowcol_to_cell(row-2,5), xl_rowcol_to_cell(row-1,5)), format_total_num)
        worksheet.write(1, 6, '=sum(%s:%s) - %s' %(xl_rowcol_to_cell(TABLE_HEADER_ROW+1,6), xl_rowcol_to_cell(row-2,6), xl_rowcol_to_cell(row-1,6)), format_total_num)

        # Initial Cap Cost totals
        worksheet.write(2, 4, '=sum(%s:%s)' %(xl_rowcol_to_cell(TABLE_HEADER_ROW+1,4), xl_rowcol_to_cell(TABLE_HEADER_ROW+20,4)), format_total_num)
        worksheet.write(2, 5, '=sum(%s:%s)' %(xl_rowcol_to_cell(TABLE_HEADER_ROW+1,5), xl_rowcol_to_cell(TABLE_HEADER_ROW+20,5)), format_total_num)
        worksheet.write(2, 6, '=sum(%s:%s)' %(xl_rowcol_to_cell(TABLE_HEADER_ROW+1,6), xl_rowcol_to_cell(TABLE_HEADER_ROW+20,6)), format_total_num)

        # O&M Cost totals
        worksheet.write(3, 4, '=%s' %xl_rowcol_to_cell(TABLE_HEADER_ROW+21,4), format_total_num)
        worksheet.write(3, 5, '=%s' %xl_rowcol_to_cell(TABLE_HEADER_ROW+21,5), format_total_num)
        worksheet.write(3, 6, '=%s' %xl_rowcol_to_cell(TABLE_HEADER_ROW+21,6), format_total_num)

        # Rehab, Replacement and Residual Costs
        worksheet.write(0, 9, 'PV (2025-60)', format_total)
        worksheet.write(0, 10, 'PV (2025-80)', format_total)
        worksheet.write(1, 8, 'Rehab+Replacement Cost (2019$)', format_total)
        worksheet.write(2, 8, 'Residual Value (2019$)', format_total)
        worksheet.write(1, 9, '=sum(%s:%s)' %(xl_rowcol_to_cell(TABLE_HEADER_ROW+22,5), xl_rowcol_to_cell(row-2,5)), format_total_num)
        worksheet.write(1, 10, '=sum(%s:%s)' %(xl_rowcol_to_cell(TABLE_HEADER_ROW+22,6), xl_rowcol_to_cell(row-2,6)), format_total_num)
        worksheet.write(2, 9, '=%s' %xl_rowcol_to_cell(row-1,5), format_total_num)
        worksheet.write(2, 10, '=%s' %xl_rowcol_to_cell(row-1,6), format_total_num)

        # YOE$ Costs that were inputs from sponsor/Arup
        worksheet.write(0, 13, 'Input Costs YOE$', format_total)
        worksheet.write(1, 12, 'Capital', format_total)
        worksheet.write(2, 12, 'O&M', format_total)
        worksheet.write(1, 13, '=sum(%s:%s)/1000000' %(xl_rowcol_to_cell(TABLE_HEADER_ROW+1,3), xl_rowcol_to_cell(TABLE_HEADER_ROW+20,3)), format_total_num_M)
        worksheet.write(2, 13, '=%s/1000000' %xl_rowcol_to_cell(TABLE_HEADER_ROW+21,3), format_total_num_M)


        print("Wrote the cost streams worksheet")
        worksheet.freeze_panes(5,7)

        return int(imp_years)





if __name__ == '__main__':
    parser = argparse.ArgumentParser(usage=USAGE)
    parser.add_argument('project_dir',
                        help="The directory with the run results csvs.")
    parser.add_argument('all_projects_dir',
                        help="The directory in which to write the Benefit/Cost summary Series")
    parser.add_argument('--bcconfig',
                        help="The configuration filename in project_dir",
                        required=False, default='BC_config.csv')
    args = parser.parse_args(sys.argv[1:])

    rr = RunResults(args.project_dir, args.bcconfig)
    rr.createBaseRunResults()

    rr.calculateDailyMetrics()

    if rr.base_results:
        rr.base_results.calculateDailyMetrics()
        rr.updateDailyMetrics()

    # save the quick summary
    if rr.base_dir:
        quicksummary_csv = os.path.join(os.getcwd(),args.all_projects_dir, "quicksummary_%s_base%s.csv"  % (rr.config.loc['Project ID'], rr.config.loc['base_dir']))
    else:
        quicksummary_csv = os.path.join(os.getcwd(),args.all_projects_dir, "quicksummary_base%s.csv"  % rr.config.loc['Project ID'])

    rr.quick_summary.to_csv(quicksummary_csv, float_format='%.5f')
    #print rr.quick_summary

    rr.calculateBenefitCosts(args.project_dir, args.all_projects_dir)
