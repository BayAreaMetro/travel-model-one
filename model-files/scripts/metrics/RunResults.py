import argparse
import collections
import operator
import os
import re
import string
import sys

import pandas as pd     # yay for DataFrames and Series!
import xlsxwriter       # for writing workbooks -- formatting is better than openpyxl
from xlsxwriter.utility import xl_range, xl_rowcol_to_cell
pd.set_option('display.precision',10)

USAGE = """

  python RunResults project_metrics_dir all_projects_metrics_dir [--bcconfig BC_config.csv]

  Configuration filename is optional.  Otherwise will use project_metrics_dir/BC_config.csv

  Processes the run results in project_metrics_dir and outputs:
  * project_metrics_dir\BC_[Project ID].xlsx with run results summary
  * all_projects_metrics_dir\[Project ID].csv with a version for rolling up

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
      # Note: The following could be moved to a centralized source if BC_config.csv files become
      # cumbersome...
      'Capital Costs'         ,   # Capital Costs
      'Annual O&M Costs'      ,   # Operations & Maintenance costs
      'Farebox Recovery Ratio',   # What percentage of O&M are expected each year
      'Life of Project'       ,   # To annualize capital costs
      'Compare'                   # one of 'baseline-scenario' or 'scenario-baseline'
      ]
    UNITS = {
      'Capital Costs'                 :'millions of $2013',
      'Annual O&M Costs'              :'millions of $2013',
      'Life of Project'               :'years',
      'Annual Capital Costs'          :'millions of $2013',
      'Annual O&M Costs not recovered':'millions of $2013',
      'Net Annual Costs'              :'millions of $2013',
    }

    # Do these ever change?  Should they go into BC_config.csv?
    PROJECTED_2040_POPULATION   = 9299150
    YEARLY_AUTO_TRIPS_PER_AUTO  = 1583

    AVERAGE_WALK_SPEED          = 3.0       # mph
    AVERAGE_BIKE_SPEED          = 12.0      # mph
    PERCENT_POP_INACTIVE        = 0.62
    ACTIVE_MIN_REQUIREMENT      = 30
    ANNUALIZATION               = 300
    WORK_ANNUALIZATION          = 250

    PERCENT_PARKING_NONHOME     = 0.5   # % of parking that occurs at a location other than one's home
    PERCENT_PARKING_WORK        = 0.5   # % of work-related trips on project route

    # In 2013 dollars.  See
    # J:\PROJECT\2013 RTP_SCS\Performance Assessment\Project Assessment (Apr 2012)\B-C Methodology\
    #    Off-Model Benefits Calculator.xlsx
    # Worksheet 'Parking Costs by County'
    # From Final Report Table 9:
    #   "For this benefit valuation, costs vary based on the average parking costs for each of 
    #    the Bay Area counties, taking into account average trip durations, parking subsidy rates,
    #    and hourly parking rates. The following per-trip parking cost savings were estimated for
    #    each auto trip reduced by county:"
    PARKING_COST_PER_TRIP_WORK = collections.OrderedDict([
    ('San Francisco',7.16),
    ('San Mateo'    ,0.0),
    ('Santa Clara'  ,0.1),
    ('Alameda'      ,0.5),
    ('Contra Costa' ,0.0),
    ('Solano'       ,0.0),
    ('Napa'         ,0.0),
    ('Sonoma'       ,0.0),
    ('Marin'        ,0.0)
    ])
    PARKING_COST_PER_TRIP_NONWORK = collections.OrderedDict([
    ('San Francisco',5.64),
    ('San Mateo'    ,0.04),
    ('Santa Clara'  ,0.33),
    ('Alameda'      ,0.39),
    ('Contra Costa' ,0.00),
    ('Solano'       ,0.00),
    ('Napa'         ,0.00),
    ('Sonoma'       ,0.00),
    ('Marin'        ,0.00)
    ])

    # From 'Plan Bay Area Performance Assessment Report_FINAL.pdf'
    # Model output only captured direct particulate matter emissions; emissions were
    # scaled up to account for particulate emissions from road dust and brake/tire
    # wear
    EMISSIONS_SCALEUP           = 1.10231
    PM25_MAGIC_A                = 0.007             # TODO: what is this?
    PM25_MAGIC_B                = 0.01891           # TODO: what is this?
    PM25_MAGIC_C                = 0.00000110231131  # TODO: what is this

    # Already annual -- don't annualize. Default false.
    ALREADY_ANNUAL = {
    ('Travel Cost','Vehicle Ownership (Modeled)'                 ): True,
    ('Travel Cost','Vehicle Ownership (Est. from Auto Trips)'    ): True,
    ('Collisions, Active Transport & Noise','Active Individuals','Total'): True,
    }

    # Already a diff -- don't diff. Default false.
    ALREADY_DIFF = {
    ('Travel Time & Cost (logsum hours)','Work & School'): True,
    ('Travel Time & Cost (logsum hours)','All'          ): True,
    }

    # default is ANNUALIZATION
    ANNUALIZATION_FACTOR = {
    ('Travel Time & Cost (logsum hours)','Work & School'): WORK_ANNUALIZATION,
    }

    # See 'Plan Bay Area Performance Assessment Report_FINAL.pdf'
    # Table 9: Benefit Valuations
    # Units in 2013 dollars
    BENEFIT_VALUATION           = {
    ('Travel Time & Cost (logsum hours)','Work & School'                       ):      16.03,
    ('Travel Time & Cost (logsum hours)','All'                                 ):      16.03,
    ('Travel Time','Auto/Truck (Hours)'                                        ):     -16.03,  # Auto
    ('Travel Time','Auto/Truck (Hours)','Truck (VHT)'                          ):     -26.24,  # Truck
    ('Travel Time','Non-Recurring Freeway Delay (Hours)','Auto (Person Hours)' ):     -16.03,
    ('Travel Time','Non-Recurring Freeway Delay (Hours)','Truck (Vehicle Hours)'):    -26.24,
    ('Travel Time','Transit In-Vehicle (Hours)'                                ):     -16.03,
    ('Travel Time','Transit Out-of-Vehicle (Hours)'                            ):     -35.266,
    ('Travel Time','Walk/Bike (Hours)'                                         ):     -16.03,
#  This is for reference - Operating Costs are calculated directly
#    ('Travel Cost','VMT','Auto'                                                ):      -0.2688,
#    ('Travel Cost','VMT','Truck'                                               ):      -0.3950,
    ('Travel Cost','Operating Costs','Auto ($2000) - Households'               ):      -1.35, # $1 in 2000 = $1.35 in 2013
    ('Travel Cost','Operating Costs','Auto ($2000) - IX/EX'                    ):      -1.35, # $1 in 2000 = $1.35 in 2013
    ('Travel Cost','Operating Costs','Auto ($2000) - AirPax'                   ):      -1.35, # $1 in 2000 = $1.35 in 2013
    ('Travel Cost','Operating Costs','Truck ($2000)'                           ):      -1.35, # $1 in 2000 = $1.35 in 2013
    ('Travel Cost','Operating Costs','Bus ($2000)'                             ):      -1.35, # $1 in 2000 = $1.35 in 2013
    ('Travel Cost','Vehicle Ownership (Modeled)'                               ):   -6290.0,
# Use modeled.  Est. from auto trips is for reference
#   ('Travel Cost','Vehicle Ownership (Est. from Auto Trips)'                  ):   -6290.0,
    ('Travel Cost','Parking Costs','Work Trips in San Francisco'               ):      -7.16,
    ('Travel Cost','Parking Costs','Work Trips in San Mateo'                   ):       0.00,
    ('Travel Cost','Parking Costs','Work Trips in Santa Clara'                 ):      -0.15,
    ('Travel Cost','Parking Costs','Work Trips in Alameda'                     ):      -0.54,
    ('Travel Cost','Parking Costs','Work Trips in Contra Costa'                ):       0.00,
    ('Travel Cost','Parking Costs','Work Trips in Solano'                      ):       0.00,
    ('Travel Cost','Parking Costs','Work Trips in Napa'                        ):       0.00,
    ('Travel Cost','Parking Costs','Work Trips in Sonoma'                      ):       0.00,
    ('Travel Cost','Parking Costs','Work Trips in Marin'                       ):       0.00,
    ('Travel Cost','Parking Costs','Non-Work Trips in San Francisco'           ):      -5.64,
    ('Travel Cost','Parking Costs','Non-Work Trips in San Mateo'               ):      -0.04,
    ('Travel Cost','Parking Costs','Non-Work Trips in Santa Clara'             ):      -0.33,
    ('Travel Cost','Parking Costs','Non-Work Trips in Alameda'                 ):      -0.39,
    ('Travel Cost','Parking Costs','Non-Work Trips in Contra Costa'            ):       0.00,
    ('Travel Cost','Parking Costs','Non-Work Trips in Solano'                  ):       0.00,
    ('Travel Cost','Parking Costs','Non-Work Trips in Napa'                    ):       0.00,
    ('Travel Cost','Parking Costs','Non-Work Trips in Sonoma'                  ):       0.00,
    ('Travel Cost','Parking Costs','Non-Work Trips in Marin'                   ):       0.00,
    ('Air Pollutant','PM2.5 (tons)','PM2.5 Gasoline'                           ): -487200.0,
    ('Air Pollutant','PM2.5 (tons)','PM2.5 Diesel'                             ): -490300.0,
    ('Air Pollutant','CO2 (metric tons)','CO2'                                 ):     -55.35,
    ('Air Pollutant','Other','NOX (tons)'                                      ):   -7800.0,
    ('Air Pollutant','Other','SO2 (tons)'                                      ):  -40500.0,
    ('Air Pollutant','Other','VOC: Acetaldehyde (metric tons)'                 ):   -5700.0,
    ('Air Pollutant','Other','VOC: Benzene (metric tons)'                      ):  -12800.0,
    ('Air Pollutant','Other','VOC: 1,3-Butadiene (metric tons)'                ):  -32200.0,
    ('Air Pollutant','Other','VOC: Formaldehyde (metric tons)'                 ):   -6400.0,
    ('Air Pollutant','Other','All other VOC (metric tons)'                     ):   -5100.0,
    ('Collisions, Active Transport & Noise','Fatalies due to Collisions'           ):-4590000.0,
    ('Collisions, Active Transport & Noise','Injuries due to Collisions'           ):  -64000.0,
    ('Collisions, Active Transport & Noise','Property Damage Only (PDO) Collisions'):   -2455.0,
    ('Collisions, Active Transport & Noise','Active Individuals'                   ):    1220.0,
    ('Collisions, Active Transport & Noise','Noise','Auto VMT'                     ):      -0.0012,
    ('Collisions, Active Transport & Noise','Noise','Truck VMT'                    ):      -0.0150,
    }

    def __init__(self, rundir, bc_config='BC_config.csv', overwrite_config=None):
        """
    Parameters
    ----------
    rundir : string
        The directory containing the raw output for the model run.
    overwrite_config : dict
        Pass overwrite config if this is a base scenario and we should use the
        project's parking costs and ovtt adjustment mode.

    Read configuration and input data.
    """
        # read the configs
        self.rundir = os.path.abspath(rundir)
        config_file = os.path.join(rundir, bc_config)
        self.config = pd.Series.from_csv(config_file, header=None, index_col=0)
        self.config['Project Run Dir'] = self.rundir

        self.base_results = None

        # Make sure required values are in the configuration
        print("Reading result csvs from '%s'" % self.rundir)
        try:
            for key in RunResults.REQUIRED_KEYS:
                unit = None
                if key in RunResults.UNITS: unit = RunResults.UNITS[key]
                config_key  = '%s (%s)' % (key,unit) if unit else key

                print("  %25s '%s'" % (config_key, self.config.loc[config_key]))

        except KeyError as e:
            print("Configuration file %s missing required variable: %s" % (config_file, str(e)))
            sys.exit(2)

        self.is_base_dir = False
        if overwrite_config:
            self.is_base_dir = True
            for key in overwrite_config.keys(): self.config[key] = overwrite_config[key]
            print "OVERWRITE_CONFIG FOR BASE_DIR: "
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

        self.vmt_vht_metrics = \
            pd.read_table(os.path.join(self.rundir, "vmt_vht_metrics.csv"),
                          sep=",", index_col=[0,1])
        # print self.vmt_vht_metrics

        self.nonmot_times = \
            pd.read_table(os.path.join(self.rundir, "nonmot_times.csv"),
                                       sep=",", index_col=[0,1])
        # print self.nonmot_times

        # self.transit_boards_miles = \
        #     pd.read_table(os.path.join(self.rundir, "transit_boards_miles.csv"),
        #                   sep=",", index_col=0)
        # print self.transit_boards_miles

        self.bus_opcost = \
            pd.read_table(os.path.join(self.rundir, "bus_opcost.csv"),
                          sep=",", index_col=[0])
        # print self.bus_opcost

        self.transit_times_by_acc_mode_egr = \
            pd.read_table(os.path.join(self.rundir, "transit_times_by_acc_mode_egr.csv"),
                          sep=",", index_col=[0,1,2])
        # print self.transit_times_by_acc_mode_egr

        self.transit_times_by_mode_income = \
            pd.read_table(os.path.join(self.rundir, "transit_times_by_mode_income.csv"),
                          sep=",", index_col=[0,1])
        # print self.transit_times_by_mode_income

        for filename in ['mandatoryAccessibilities', 'nonMandatoryAccessibilities']:
            accessibilities = \
                pd.read_table(os.path.join(self.rundir, "..", "accessibilities", "%s.csv" % filename),
                              sep=",")
            accessibilities.drop('destChoiceAlt', axis=1, inplace=True)
            accessibilities.set_index(['taz','subzone'], inplace=True)
            # put 'lowInc_0_autos' etc are in a column not column headers
            accessibilities = pd.DataFrame(accessibilities.stack())
            accessibilities.reset_index(inplace=True)
            # split the income/auto sufficiency column into two columns
            incQ_autoSuff = accessibilities['level_2'].str.split('_', n=1).apply(pd.Series)
            incQ_autoSuff.columns = ['incQ_label', 'autoSuff_label']
            # add them back to the original dataframe
            accessibilities = pd.concat([incQ_autoSuff, accessibilities], axis=1)
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
        except:
            # this is ok -- no base_dir specified
            self.base_dir     = None

        if self.base_dir:
            # these are not ok - let exceptions raise
            print("")
            print("BASE:")
            self.base_dir = os.path.realpath(self.base_dir)

            # pass the parking config for overwrite
            base_overwrite_config = {}
            total_parking_cost_allocation = 0.0
            for county in RunResults.PARKING_COST_PER_TRIP_WORK.keys():
                key = 'percent parking cost incurred in %s' % county
                # convert to floats
                self.config.loc[key] = float(self.config.loc[key])
                base_overwrite_config[key] = self.config.loc[key]
                total_parking_cost_allocation += self.config.loc[key]

            assert(abs(total_parking_cost_allocation - 1.0) < 0.001)

            # pass the project mode for overwrite to base
            base_overwrite_config['Project Mode'] = self.config.loc['Project Mode']

            print self.base_dir
            print base_overwrite_config
            self.base_results = RunResults(rundir = self.base_dir,
                                           overwrite_config=base_overwrite_config)

    def calculateDailyMetrics(self):
        """
        Calculates the daily output metrics which will actually get used for the benefits/cost
        analysis.
        """

        # we really want these by class -- ignore time periods and income levels
        vmt_byclass     = self.vmt_vht_metrics.sum(level='vehicle class') # vehicles, not people
        transit_byclass = self.transit_times_by_acc_mode_egr.sum(level='Mode')
        transit_byaceg  = self.transit_times_by_acc_mode_egr.sum(level=['Access','Egress'])
        nonmot_byclass  = self.nonmot_times.sum(level='Mode')             # person trips
        auto_byclass    = self.auto_times.sum(level='Mode')               # person trips

        daily_results   = collections.OrderedDict()
        ######################################################################################
        cat1            = 'Travel Time & Cost (logsum hours)'
        if self.base_results:
            # Take the difference and convert utils to minutes (k_ivt = 0.0134 k_mc_ls = 1.0 in access calcs);
            # TODO: is k_mc_ls = 1.0?  DestinationChoice.cls has different values
            self.mandatoryAccessibilities = pd.merge(self.mandatoryAccessibilities,
                                                     self.base_results.mandatoryAccessibilities,
                                                    how='left')
            self.mandatoryAccessibilities['diff_dclogsum'] = \
                self.mandatoryAccessibilities.scen_dclogsum - self.mandatoryAccessibilities.base_dclogsum
            self.mandatoryAccessibilities['logsum_diff_minutes'] = self.mandatoryAccessibilities.diff_dclogsum / 0.0134

            # This too
            self.nonmandatoryAccessibilities = pd.merge(self.nonmandatoryAccessibilities,
                                                        self.base_results.nonmandatoryAccessibilities,
                                                        how='left')
            self.nonmandatoryAccessibilities['diff_dclogsum'] = \
                self.nonmandatoryAccessibilities.scen_dclogsum - self.nonmandatoryAccessibilities.base_dclogsum
            self.nonmandatoryAccessibilities['logsum_diff_minutes'] = self.nonmandatoryAccessibilities.diff_dclogsum / 0.0175


            # print "self.mandatoryAccessibilities"
            # print len(self.mandatoryAccessibilities)
            # print self.mandatoryAccessibilities.head()

            # print "self.nonmandatoryAccessibilities"
            # print len(self.nonmandatoryAccessibilities)
            # print self.nonmandatoryAccessibilities.head()

            self.accessibilityMarkets = pd.merge(self.accessibilityMarkets,
                                                 self.base_results.accessibilityMarkets,
                                                 how='left')
            # print "self.accessibilityMarkets"
            # print len(self.accessibilityMarkets)
            # print self.accessibilityMarkets.head()

            self.mandatoryAccess = pd.merge(self.mandatoryAccessibilities,
                                            self.accessibilityMarkets,
                                            how='left')
            self.mandatoryAccess.fillna(0)
            # print "self.mandatoryAccess"
            # print len(self.mandatoryAccess)
            # print self.mandatoryAccess.head()

            self.nonmandatoryAccess = pd.merge(self.nonmandatoryAccessibilities,
                                               self.accessibilityMarkets,
                                               how='left')
            self.nonmandatoryAccess.fillna(0)
            # print "self.nonmandatoryAccess"
            # print len(self.nonmandatoryAccess)
            # print self.nonmandatoryAccess.head()

            # rule of one-half
            # to compare with AccessibilityDifference.csv -- workers only
            # test = self.mandatoryAccess.loc[(self.mandatoryAccess.base_num_workers > 0) &
            #                                 (self.mandatoryAccess.scen_num_workers > 0), :]
            # test['base_weight_diff']      = test.base_num_workers*test.logsum_diff_minutes
            # test['scen_weight_diff']      = test.scen_num_workers*test.logsum_diff_minutes
            # test['consumer_surplus_diff'] = 0.5*test.base_weight_diff + 0.5*test.scen_weight_diff
            # test = test[['taz','logsum_diff_minutes','base_weight_diff','scen_weight_diff','consumer_surplus_diff']]
            # test = test.groupby(['taz']).sum()
            # test.to_csv(os.path.join(self.rundir,'AccessibilityDifference_workers.csv'), header=True, float_format='%.6f')

            cat2         = 'Work & School'
            self.mandatoryAccess['CS diff work/school'] = \
                (0.5*self.mandatoryAccess.base_num_workers_students + 0.5*self.mandatoryAccess.scen_num_workers_students) *self.mandatoryAccess.logsum_diff_minutes
            for inclabel in ['lowInc','medInc','highInc','veryHighInc']:
                daily_results[(cat1,cat2,inclabel)] = self.mandatoryAccess.loc[self.mandatoryAccess.incQ_label==inclabel, 'CS diff work/school'].sum()/60.0;

            cat2         = 'All'
            self.nonmandatoryAccess['CS diff all'] = \
                (0.5*self.nonmandatoryAccess.base_num_persons + 0.5*self.nonmandatoryAccess.scen_num_persons)*self.nonmandatoryAccess.logsum_diff_minutes
            for inclabel in ['lowInc','medInc','highInc','veryHighInc']:
                daily_results[(cat1,cat2,inclabel)] = self.nonmandatoryAccess.loc[self.mandatoryAccess.incQ_label==inclabel, 'CS diff all'].sum()/60.0;


        ######################################################################################
        cat1            = 'Travel Time'
        cat2            = 'Auto/Truck (Hours)'
        daily_results[(cat1,cat2,'SOV (PHT)'  )] = vmt_byclass.loc[['DA','DAT'],'VHT'].sum()
        daily_results[(cat1,cat2,'HOV2 (PHT)' )] = vmt_byclass.loc[['S2','S2T'],'VHT'].sum()*2
        daily_results[(cat1,cat2,'HOV3+ (PHT)')] = vmt_byclass.loc[['S3','S3T'],'VHT'].sum()*3.5
        daily_results[(cat1,cat2,'Truck (VHT)')] = vmt_byclass.loc[['SM','SMT','HV','HVT'],'VHT'].sum()

        # These are from vehicle hours -- make them person hours
        cat2            = 'Non-Recurring Freeway Delay (Hours)'
        daily_results[(cat1,cat2,'Auto (Person Hours)')] = \
            vmt_byclass.loc[['DA','DAT'],'Non-Recurring Freeway Delay'].sum()   +\
            vmt_byclass.loc[['S2','S2T'],'Non-Recurring Freeway Delay'].sum()*2 +\
            vmt_byclass.loc[['S3','S3T'],'Non-Recurring Freeway Delay'].sum()*3.5
        daily_results[(cat1,cat2,'Truck (Vehicle Hours)')] = \
            vmt_byclass.loc[['SM','SMT','HV','HVT'],'Non-Recurring Freeway Delay'].sum()

        cat2            = 'Transit In-Vehicle (Hours)'
        daily_results[(cat1,cat2,'Local Bus'       )] = transit_byclass.loc['loc','In-vehicle hours']
        daily_results[(cat1,cat2,'Light Rail/Ferry')] = transit_byclass.loc['lrf','In-vehicle hours']
        daily_results[(cat1,cat2,'Express Bus'     )] = transit_byclass.loc['exp','In-vehicle hours']
        daily_results[(cat1,cat2,'Heavy Rail'      )] = transit_byclass.loc['hvy','In-vehicle hours']
        daily_results[(cat1,cat2,'Commuter Rail'   )] = transit_byclass.loc['com','In-vehicle hours']

        cat2            = 'Transit Out-of-Vehicle (Hours)'
        daily_results[(cat1,cat2,'Walk Access+Egress' )] = transit_byclass.loc[:,'Walk acc & egr hours'].sum() + \
                                                     transit_byclass.loc[:,'Aux walk hours'].sum()
        daily_results[(cat1,cat2,'Drive Access+Egress')] = transit_byclass.loc[:,'Drive acc & egr hours'].sum()
        daily_results[(cat1,cat2,'Wait'               )] = transit_byclass.loc[:,'Init wait hours'].sum() + \
                                                     transit_byclass.loc[:,'Xfer wait hours'].sum()
        # Out-of-Vehicle adjustment
        auto_person_trips    = auto_byclass.loc[['da','datoll','sr2','sr2toll','sr3','sr3toll'],'Daily Person Trips'].sum()
        transit_person_trips = transit_byclass.loc[:,'Transit Trips'].sum()
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

        ######################################################################################
        cat1            = 'Travel Cost'
        cat2            = 'VMT (Reference)'
        daily_results[(cat1,cat2,'Auto' )] = \
            vmt_byclass.loc[['DA','DAT','S2','S2T','S3','S3T'],'VMT'].sum()
        daily_results[(cat1,cat2,'Truck')] = \
            vmt_byclass.loc[['SM','SMT','HV','HVT'],'VMT'].sum()
        daily_results[(cat1,cat2,'Truck from Trips+Skims')] = \
            auto_byclass.loc['truck','Vehicle Miles']

        cat2            = 'Operating Costs'
        daily_results[(cat1,cat2,'Auto ($2000) - Households' )] = \
            0.01*auto_byclass.loc[['da','datoll','sr2','sr2toll','sr3','sr3toll'],'Total Cost'].sum()
        daily_results[(cat1,cat2,'Auto ($2000) - IX/EX' )] = \
            0.01*auto_byclass.loc[['da_ix','datoll_ix','sr2_ix','sr2toll_ix','sr3_ix','sr3toll_ix'],'Total Cost'].sum()
        daily_results[(cat1,cat2,'Auto ($2000) - AirPax' )] = \
            0.01*auto_byclass.loc[['da_air','datoll_air','sr2_air','sr2toll_air','sr3_air','sr3toll_air'],'Total Cost'].sum()
        daily_results[(cat1,cat2,'Truck ($2000)')] = \
            0.01*auto_byclass.loc['truck','Total Cost'].sum()
        daily_results[(cat1,cat2,'Bus ($2000)')] = self.bus_opcost['opcost'].sum()

        # Parking
        cat2            = 'Trips (Reference)'
        daily_results[(cat1,cat2,'Vehicle trips: SOV'  )] = auto_byclass.loc[['da' ,'datoll' ],'Daily Vehicle Trips'].sum()
        daily_results[(cat1,cat2,'Vehicle trips: HOV2' )] = auto_byclass.loc[['sr2','sr2toll'],'Daily Vehicle Trips'].sum()
        daily_results[(cat1,cat2,'Vehicle trips: HOV3+')] = auto_byclass.loc[['sr3','sr3toll'],'Daily Vehicle Trips'].sum()
        total_autotrips = daily_results[(cat1,cat2,'Vehicle trips: SOV')] + \
                          daily_results[(cat1,cat2,'Vehicle trips: HOV2')] + \
                          daily_results[(cat1,cat2,'Vehicle trips: HOV3+')]
        daily_results[(cat1,cat2,'Truck Trips')]         = auto_byclass.loc['truck', 'Daily Vehicle Trips']
        daily_results[(cat1,cat2,'Drive+Transit Trips')] = transit_byaceg.loc[[('wlk','drv'),('drv','wlk')],'Transit Trips'].sum()
        daily_results[(cat1,cat2,'Walk +Transit Trips')] = transit_byaceg.loc[('wlk','wlk'),'Transit Trips'].sum()

        cat2            = 'Parking Costs'
        try:
            for county in RunResults.PARKING_COST_PER_TRIP_WORK.keys():
                daily_results[(cat1,cat2,'Work Trips in %s'     % county)] = total_autotrips * \
                    RunResults.PERCENT_PARKING_NONHOME * RunResults.PERCENT_PARKING_WORK * \
                    float(self.config.loc['percent parking cost incurred in %s' % county])
            for county in RunResults.PARKING_COST_PER_TRIP_WORK.keys():
                daily_results[(cat1,cat2,'Non-Work Trips in %s' % county)] = total_autotrips * \
                    RunResults.PERCENT_PARKING_NONHOME * (1.0-RunResults.PERCENT_PARKING_WORK) * \
                    float(self.config.loc['percent parking cost incurred in %s' % county])
        except:
            # base dirs don't have parking costs
            assert(self.is_base_dir)

        # Vehicles Owned
        cat2            = 'Vehicle Ownership (Modeled)'
        daily_results[(cat1,cat2,'Total')] = self.autos_owned['total autos'].sum()

        # Vehicles Owned - estimated from auto trips
        cat2            = 'Vehicle Ownership (Est. from Auto Trips)'
        daily_results[(cat1,cat2,'Total')] =total_autotrips*RunResults.ANNUALIZATION/RunResults.YEARLY_AUTO_TRIPS_PER_AUTO

        ######################################################################################
        cat1            = 'Air Pollutant'
        cat2            = 'PM2.5 (tons)'
        daily_results[(cat1,cat2,'PM2.5 Gasoline')] = \
            vmt_byclass.loc[:,'Gas_PM2.5'].sum()*RunResults.EMISSIONS_SCALEUP + \
            (daily_results[('Travel Cost','VMT (Reference)','Auto')]*(RunResults.PM25_MAGIC_A+RunResults.PM25_MAGIC_B)*RunResults.PM25_MAGIC_C)
        daily_results[(cat1,cat2,'PM2.5 Diesel'  )] = \
            vmt_byclass.loc[:,'Diesel_PM2.5'].sum()*RunResults.EMISSIONS_SCALEUP + \
            (daily_results[('Travel Cost','VMT (Reference)','Truck')]*(RunResults.PM25_MAGIC_A+RunResults.PM25_MAGIC_B)*RunResults.PM25_MAGIC_C)

        cat2            = 'CO2 (metric tons)'
        daily_results[(cat1,cat2,'CO2')] = vmt_byclass.loc[:,'CO2'  ].sum()

        cat2            = 'Other'
        daily_results[(cat1,cat2,'NOX (tons)')] = vmt_byclass.loc[:,'W_NOx'].sum()*RunResults.EMISSIONS_SCALEUP
        daily_results[(cat1,cat2,'SO2 (tons)')] = vmt_byclass.loc[:,'SOx'  ].sum()*RunResults.EMISSIONS_SCALEUP

        # http://en.wikipedia.org/wiki/Volatile_organic_compound
        daily_results[(cat1,cat2,'VOC: Acetaldehyde (metric tons)' )] = vmt_byclass.loc[:,'Acetaldehyde'  ].sum()*RunResults.EMISSIONS_SCALEUP
        daily_results[(cat1,cat2,'VOC: Benzene (metric tons)'      )] = vmt_byclass.loc[:,'Benzene'       ].sum()*RunResults.EMISSIONS_SCALEUP
        daily_results[(cat1,cat2,'VOC: 1,3-Butadiene (metric tons)')] = vmt_byclass.loc[:,'Butadiene'     ].sum()*RunResults.EMISSIONS_SCALEUP
        daily_results[(cat1,cat2,'VOC: Formaldehyde (metric tons)' )] = vmt_byclass.loc[:,'Formaldehyde'  ].sum()*RunResults.EMISSIONS_SCALEUP
        daily_results[(cat1,cat2,'All other VOC (metric tons)'     )] = vmt_byclass.loc[:,'ROG'].sum()*RunResults.EMISSIONS_SCALEUP \
            - daily_results[(cat1,cat2,'VOC: Acetaldehyde (metric tons)' )] \
            - daily_results[(cat1,cat2,'VOC: Benzene (metric tons)'      )] \
            - daily_results[(cat1,cat2,'VOC: 1,3-Butadiene (metric tons)')] \
            - daily_results[(cat1,cat2,'VOC: Formaldehyde (metric tons)' )]

        ######################################################################################
        cat1            = 'Collisions, Active Transport & Noise'
        cat2            = 'Fatalies due to Collisions'
        daily_results[(cat1,cat2,'Motor Vehicle')] = vmt_byclass.loc[:,'Motor Vehicle Fatality'].sum()
        daily_results[(cat1,cat2,'Walk'         )] = vmt_byclass.loc[:,'Walk Fatality'         ].sum()
        daily_results[(cat1,cat2,'Bike'         )] = vmt_byclass.loc[:,'Bike Fatality'         ].sum()

        cat2            = 'Injuries due to Collisions'
        daily_results[(cat1,cat2,'Motor Vehicle')] = vmt_byclass.loc[:,'Motor Vehicle Injury'  ].sum()
        daily_results[(cat1,cat2,'Walk'         )] = vmt_byclass.loc[:,'Walk Injury'           ].sum()
        daily_results[(cat1,cat2,'Bike'         )] = vmt_byclass.loc[:,'Bike Injury'           ].sum()

        cat2           = 'Property Damage Only (PDO) Collisions'
        daily_results[(cat1,cat2,'Property Damage')] = vmt_byclass.loc[:,'Motor Vehicle Property'].sum()

        ######################################################################################
        cat2         = 'Trips with Active Transportation'
        # "Off-Model Benefits" -- see
        # J:\PROJECT\2013 RTP_SCS\Performance Assessment\Project Assessment (Apr 2012)\B-C Methodology\Off-Model Benefits Calculator.xlsx
        daily_results[(cat1,cat2,'Walk'   )] = nonmot_byclass.loc['Walk','Daily Trips']
        daily_results[(cat1,cat2,'Bike'   )] = nonmot_byclass.loc['Bike','Daily Trips']
        daily_results[(cat1,cat2,'Transit')] = transit_byclass.loc[:,'Transit Trips'].sum() # all transit trips

        cat2         = 'Avg Minutes Active Transport per Person'
        daily_results[(cat1,cat2,'Walk'   )] = nonmot_byclass.loc['Walk','Total Time (Hours)'] * 60.0 / RunResults.PROJECTED_2040_POPULATION
        daily_results[(cat1,cat2,'Bike'   )] = nonmot_byclass.loc['Bike','Total Time (Hours)'] * 60.0 / RunResults.PROJECTED_2040_POPULATION
        daily_results[(cat1,cat2,'Transit')] = (transit_byclass.loc[:,'Walk acc & egr hours'].sum() + \
                                          transit_byclass.loc[:,'Aux walk hours'].sum()) * 60.0 / RunResults.PROJECTED_2040_POPULATION
        avg_min_total = daily_results[(cat1,cat2,'Walk'   )] + \
                        daily_results[(cat1,cat2,'Bike'   )] + \
                        daily_results[(cat1,cat2,'Transit')]

        cat2         = 'Active Individuals'
        # (active daily min per bay area person) * (inactive persons) = 
        #            total active daily min per day _by inactive persons_
        # Divide by active minute per day requirement to get "active people"
        # TODO: Why multiply by inactive population?
        #       Are we just removing the population that is assumed to be active anyway?
        #       Wouldn't subtracting the the base give newly active population?
        daily_results[(cat1,cat2,'Total'  )] = avg_min_total * \
            (RunResults.PERCENT_POP_INACTIVE * RunResults.PROJECTED_2040_POPULATION) / RunResults.ACTIVE_MIN_REQUIREMENT

        # Noise
        cat2            = 'Noise'
        daily_results[(cat1,cat2,'Auto VMT')] = \
            vmt_byclass.loc[['DA','DAT','S2','S2T','S3','S3T'],'VMT'].sum()
        daily_results[(cat1,cat2,'Truck VMT')] = \
            vmt_byclass.loc[['SM','SMT','HV','HVT'],'VMT'].sum()

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
        print self.daily_category_results

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
            base_str_re = re.compile("(19|20)[0-9][0-9]_05_[A-Za-z0-9]{3}[^\\\]*")
            base_match  = base_str_re.search(self.config.loc['base_dir'])
            if base_match:
                self.config['Base Project ID'] = base_match.group(0)
                self.config['Project Compare ID'] = "%s vs %s" % (self.config.loc['Project ID'], base_match.group(0))
                # print "base_match = [%s]" % base_match.group(0)
                workbook_name = "BC_%s_base%s.xlsx" % (self.config.loc['Project ID'], base_match.group(0))
                csv_name      = "BC_%s_base%s.csv"  % (self.config.loc['Project ID'], base_match.group(0))

        BC_detail_workbook = os.path.join(project_dir, workbook_name)
        workbook        = xlsxwriter.Workbook(BC_detail_workbook)
        scen_minus_base = self.writeBCWorksheet(workbook)

        if self.base_dir:
            base_minus_scen = self.writeBCWorksheet(workbook, scen_minus_baseline=False)
        workbook.close()
        print("Wrote %s" % BC_detail_workbook)

        if self.base_dir:
            bc_metrics = None
            if self.config.loc['Compare'] == 'scenario-baseline':
                bc_metrics = scen_minus_base
            elif self.config.loc['Compare'] == 'baseline-scenario':
                bc_metrics = base_minus_scen

            idx = pd.MultiIndex.from_tuples(bc_metrics.keys(), 
                                            names=['category1','category2','category3','variable_name'])
            self.bc_metrics = pd.Series(bc_metrics, index=idx)
            self.bc_metrics.name = 'values'

            all_proj_filename = os.path.join(all_projects_dir, csv_name)
            self.bc_metrics.to_csv(all_proj_filename, header=True, float_format='%.5f')
            print("Wrote %s" % all_proj_filename)

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
            unit = None
            if key in RunResults.UNITS: unit = RunResults.UNITS[key]

            config_key  = '%s (%s)' % (key,unit) if unit else key
            try:    val = float(self.config.loc[config_key])
            except: val = self.config.loc[config_key]

            worksheet.write(row,1, val, 
                            format_highlight_money if string.find(key,'Costs') >= 0 else format_highlight)
            for col in range(2,5): worksheet.write(row,col,"",format_highlight)

            if unit: worksheet.write(row,2, '(%s)' % unit,format_highlight)
            row += 1

        # Run directory
        if self.base_dir:
            worksheet.write(row,0, "Base Run Dir", format_label)
            worksheet.merge_range(row,1,row,4, self.base_dir, format_highlight_file)
            worksheet.set_row(row,36.0)
        row += 1

        # Comparison type
        worksheet.write(row,0, 'Compare', format_label)
        worksheet.write(row,1, self.config.loc['Compare'], format_highlight)
        for col in range(2,5): worksheet.write(row,col,"",format_highlight)
        row += 1

        # Calculated from config
        format_highlight= workbook.add_format({'bg_color':'#FFFFC0'})
        format_highlight_money = workbook.add_format({'bg_color':'#FFFFC0',
                                                     'num_format':'_($* #,##0.0_);_($* (#,##0.0);_($* "-"_);_(@_)'})

        # Annual Capital Costs
        worksheet.write(row,0, 'Annual Capital Costs', format_label)
        worksheet.write(row,1, '=%s/%s' % 
                        (xl_rowcol_to_cell(RunResults.REQUIRED_KEYS.index('Capital Costs')+2,1), 
                         xl_rowcol_to_cell(RunResults.REQUIRED_KEYS.index('Life of Project')+2,1)),
                         format_highlight_money)
        worksheet.write(row,2, '(%s)' % RunResults.UNITS['Annual Capital Costs'], format_highlight)
        for col in range(3,5): worksheet.write(row,col,"",format_highlight)
        bc_metrics[('Annual Capital Costs (%s)' % RunResults.UNITS['Annual Capital Costs'],"","","")] = \
            float(self.config.loc['Capital Costs (%s)' % RunResults.UNITS['Capital Costs']]) / \
            float(self.config.loc['Life of Project (%s)' % RunResults.UNITS['Life of Project']])
        row += 1

        # Annual O&M Costs not recovered
        worksheet.write(row,0, 'Annual O&M Costs not recovered', format_label)
        worksheet.write(row,1, '=%s*(1-%s)' % 
                        (xl_rowcol_to_cell(RunResults.REQUIRED_KEYS.index('Annual O&M Costs')+2,1), 
                         xl_rowcol_to_cell(RunResults.REQUIRED_KEYS.index('Farebox Recovery Ratio')+2,1)),
                         format_highlight_money)
        worksheet.write(row,2, '(%s)' % RunResults.UNITS['Annual O&M Costs not recovered'],
                        format_highlight)
        for col in range(3,5): worksheet.write(row,col,"",format_highlight)
        bc_metrics[('Annual O&M Costs not recovered (%s)' % RunResults.UNITS['Annual O&M Costs not recovered'],"","","")] = \
            float(self.config.loc['Annual O&M Costs (%s)' % RunResults.UNITS['Annual O&M Costs']])* \
            (1.0-float(self.config.loc['Farebox Recovery Ratio']))
        row += 1

        # Net Annual Costs
        worksheet.write(row,0, 'Net Annual Costs', format_label)
        worksheet.write(row,1, '=%s+%s' %  (xl_rowcol_to_cell(row-2,1), xl_rowcol_to_cell(row-1,1)),
                        format_highlight_money)
        worksheet.write(row,2, '(%s)' % RunResults.UNITS['Net Annual Costs'], format_highlight)
        ANNUAL_COSTS_CELL = xl_rowcol_to_cell(row,1)
        for col in range(3,5): worksheet.write(row,col,"",format_highlight)
        bc_metrics[('Net Annual Costs (%s)' % RunResults.UNITS['Net Annual Costs'],"","","")] = \
            bc_metrics[('Annual Capital Costs (%s)' % RunResults.UNITS['Annual Capital Costs'],"","","")] + \
            bc_metrics[('Annual O&M Costs not recovered (%s)' % RunResults.UNITS['Annual O&M Costs not recovered'],"","","")]
        row += 1

        # Header row
        row += 1 # space
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
            worksheet.write(row,8,"Annual\nBenefit ($2013)",format_header)

        # Data rows
        row  += 1
        cat1 = None
        cat2 = None
        format_cat1     = workbook.add_format({'bold':True, 'bg_color':'#C5D9F1'})
        format_cat1_sum = workbook.add_format({'bold':True, 'bg_color':'#C5D9F1', 'num_format':'_(\$* #,##0.0"M"_);_(\$* (#,##0.0"M");_(\$* "-"??_);_(@_)'})
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

        # for cat1 sums (total benefits for cat1)
        cat1_sums = collections.OrderedDict() # cell -> [cell1, cell2, cell3...]
        cat1_cell = None

        for key,value in colA.daily_results.iteritems():

            # What's the valuation of this metric?
            valuation = None
            if (key[0],key[1],key[2]) in RunResults.BENEFIT_VALUATION:
                valuation = RunResults.BENEFIT_VALUATION[(key[0],key[1],key[2])]
            elif (key[0],key[1]) in RunResults.BENEFIT_VALUATION:
                valuation = RunResults.BENEFIT_VALUATION[(key[0],key[1])]
            else:
                # these are purely informational
                print("Could not lookup benefit valuation for %s" % str(key))

            # is this already a diff (e.g. no diff)
            already_diff = False
            if (key[0],key[1]) in RunResults.ALREADY_DIFF:
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
                    if cat1_cell:
                        worksheet.write(cat1_cell, 
                                        '=SUM(%s)/1000000' % str(',').join(cat1_sums[cat1_cell]),
                                        format_cat1_sum)
                    cat1_cell = xl_rowcol_to_cell(row,8)
                    cat1_sums[cat1_cell] = []

                    worksheet.write(row,2,"",format_cat1)
                    worksheet.write(row,3,"",format_cat1)
                    worksheet.write(row,4,"",format_cat1)
                    worksheet.write(row,5,"",format_cat1)
                    worksheet.write(row,6,"",format_cat1)
                    worksheet.write(row,7,"",format_cat1)
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

                if self.base_dir:
                    if cat1 in colB.daily_results and cat2 in colB.daily_results[cat1]:
                        worksheet.write(row,2, # base
                                        '=SUM(%s)' % xl_range(row+1,2,row+len(colB.daily_results[cat1][cat2]),2),
                                        format_cat2b_lil if (cat1,cat2) in self.lil_cats else format_cat2b_big)

                    if already_annual and cat1 in colB.daily_results and cat2 in colB.daily_results[cat1]:
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

                        cat1_sums[cat1_cell].append(xl_rowcol_to_cell(row,8))
                row += 1

            # details
            worksheet.write(row,0,key[2],format_var)

            worksheet.write(row,1 if not already_diff else 3,value,
                            format_val_lil if (cat1,cat2) in self.lil_cats else format_val_big)

            if already_diff:
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

                if already_annual:
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
                        bc_metrics[(cat1,cat2,key[2],'Daily Percent Difference')] = bc_metrics[(cat1,cat2,key[2],'Daily Difference')] / \
                                                                            colB.daily_results[cat1][cat2][key[2]]
                    worksheet.write(row,4, # diff annual
                                    '=%d*%s' % (annualization, xl_rowcol_to_cell(row,3)),
                                    format_val_lil if (cat1,cat2) in self.lil_cats else format_val_big)
                    bc_metrics[(cat1,cat2,key[2],'Annual Difference')] = annualization*bc_metrics[(cat1,cat2,key[2],'Daily Difference')]

                    if already_diff:
                        nominal_diff = annualization * colA.daily_results[cat1][cat2][key[2]]
                    else:
                        nominal_diff = annualization * (colA.daily_results[cat1][cat2][key[2]] - \
                                                        colB.daily_results[cat1][cat2][key[2]])

                if valuation != None:
                    worksheet.write(row,6, # diff annual
                                    valuation,
                                    format_benval_lil if abs(valuation)<1000 else format_benval_big)
                    worksheet.write(row,8, # annual benefit
                                    '=%s*%s' % (xl_rowcol_to_cell(row,4), xl_rowcol_to_cell(row,6)),
                                    format_ann_ben)
                    bc_metrics[(cat1,cat2,key[2],'Annual Benefit ($2013)')] = valuation*nominal_diff

            row += 1

        # The last cat1 sum
        if self.base_dir:
            if cat1_cell:
                worksheet.write(cat1_cell, 
                                '=SUM(%s)/1000000' % str(',').join(cat1_sums[cat1_cell]),
                                format_cat1_sum)

            # BENEFIT/COST
            format_bc_header = workbook.add_format({'bg_color':'#92D050', 'align':'right','bold':True})
            worksheet.write(TABLE_HEADER_ROW-4, 6, "Benefit"  ,format_bc_header)
            worksheet.write(TABLE_HEADER_ROW-3, 6, "Cost"     ,format_bc_header)
            worksheet.write(TABLE_HEADER_ROW-2, 6, "B/C Ratio",format_bc_header)

            worksheet.write(TABLE_HEADER_ROW-4, 7, "",format_bc_header)
            worksheet.write(TABLE_HEADER_ROW-3, 7, "",format_bc_header)
            worksheet.write(TABLE_HEADER_ROW-2, 7, "",format_bc_header)

            format_bc_money = workbook.add_format({'bg_color':'#92D050','bold':True,
                                                  'num_format':'_(\$* #,##0.0"M"_);_(\$* (#,##0.0"M");_(\$* "-"??_);_(@_)'})
            format_bc_ratio = workbook.add_format({'bg_color':'#92D050','bold':True,'num_format':'0.00'})
            worksheet.write(TABLE_HEADER_ROW-4, 8, "=SUM(%s)" % str(",").join(cat1_sums.keys()[1:]), format_bc_money)  # skip first one = logsums
            worksheet.write(TABLE_HEADER_ROW-3, 8, "=%s" % ANNUAL_COSTS_CELL, format_bc_money)
            worksheet.write(TABLE_HEADER_ROW-2, 8, "=%s/%s" % (xl_rowcol_to_cell(TABLE_HEADER_ROW-4, 8),
                                                                      xl_rowcol_to_cell(TABLE_HEADER_ROW-3, 8)),
                            format_bc_ratio)

        worksheet.set_column(0,0,40.0)
        worksheet.set_column(1,8,13.0)
        worksheet.set_column(5,5,2.0)
        worksheet.set_column(7,7,2.0)
        worksheet.set_column(8,8,15.0)
        worksheet.set_column(9,9,2.0)

        # THIS IS COBRA
        format_red      = workbook.add_format({'font_color':'white','bg_color':'#C0504D','align':'right','bold':True})
        for row in range(1,9):
            for col in range(10,13):
                worksheet.write(row,col,"",format_red)
        worksheet.write(1,10,"co",format_red)
        worksheet.write(2,10,"b" ,format_red)
        worksheet.write(3,10,"r" ,format_red)
        worksheet.write(4,10,"a" ,format_red)
        format_red      = workbook.add_format({'font_color':'white','bg_color':'#C0504D'})
        worksheet.write(1,11,"st",format_red)
        worksheet.write(2,11,"enefit" ,format_red)
        worksheet.write(3,11,"results" ,format_red)
        worksheet.write(4,11,"nalyzer" ,format_red)
        worksheet.set_column(11,11,8.0)
        worksheet.set_column(12,12,15.0)

        worksheet.insert_image(2, 12, 
                               os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "King-cobra.png"),
                               {'x_scale':0.1, 'y_scale':0.1})
        return bc_metrics

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
    if rr.base_results: rr.base_results.calculateDailyMetrics()

    rr.calculateBenefitCosts(args.project_dir, args.all_projects_dir)
