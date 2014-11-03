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

USAGE = """

  python RunResults project_dir all_projects.xlsx

  Processes the run results in project_dir and outputs project_dir\BC.xlsx with run results summary.
"""

class RunResults:
    """
    This represents the run results for a single model run, to be used to calculate
    the benefits/costs results from comparing two runs.
    """

    # Required keys for each project in the BC_config.csv
    REQUIRED_KEYS = [
      'Project ID',
      'Project Name',
      'County',
      'Project Type',
      'Project Capital Costs (millions of $2013)',
      'Net Annual O&M Costs (millions of $2013)']

    # Do these ever change?  Should they go into BC_config.csv?
    PROJECTED_2040_POPULATION   = 9299150
    AVERAGE_WALK_SPEED          = 3.0       # mph
    AVERAGE_BIKE_SPEED          = 12.0      # mph
    PERCENT_POP_INACTIVE        = 0.62
    ACTIVE_MIN_REQUIREMENT      = 30
    ANNUALIZATION               = 300

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
    PARKING_COST_PER_TRIP_WORK = collections.OrderedDict({
    'San Francisco': 7.16,
    'San Mateo'    : 0.00,
    'Santa Clara'  : 0.15,
    'Alameda'      : 0.54,
    'Contra Costa' : 0.00,
    'Solano'       : 0.00,
    'Napa'         : 0.00,
    'Sonoma'       : 0.00,
    'Marin'        : 0.00
    })
    PARKING_COST_PER_TRIP_NONWORK = collections.OrderedDict({
    'San Francisco': 5.64,
    'San Mateo'    : 0.04,
    'Santa Clara'  : 0.33,
    'Alameda'      : 0.39,
    'Contra Costa' : 0.00,
    'Solano'       : 0.00,
    'Napa'         : 0.00,
    'Sonoma'       : 0.00,
    'Marin'        : 0.00
    })

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
    ('Travel Cost','Vehicle Ownership'): True,
    ('Collisions & Active Transport','Active Individuals','Total'): True,
    }

    # See 'Plan Bay Area Performance Assessment Report_FINAL.pdf'
    # Table 9: Benefit Valuations
    # Units in dollars
    BENEFIT_VALUATION           = {
    ('Travel Time','Auto/Truck (Hours)'                         ):     -16.03,  # Auto
    ('Travel Time','Auto/Truck (Hours)','Truck (VHT)'           ):     -26.24,  # Truck
    ('Travel Time','Non-Recurring Freeway Delay (Hours)','Auto' ):     -16.03,
    ('Travel Time','Non-Recurring Freeway Delay (Hours)','Truck'):     -26.24,
    ('Travel Time','Transit In-Vehicle (Hours)'                 ):     -16.03,
    ('Travel Time','Transit Out-of-Vehicle (Hours)'             ):     -35.27,
    ('Travel Time','Walk/Bike (Hours)'                          ):     -16.03,
    ('Travel Cost','VMT','Auto'                                 ):      -0.2688,
    ('Travel Cost','VMT','Truck'                                ):      -0.3950,
    ('Travel Cost','Vehicle Ownership'                          ):   -6290.0,
    ('Air Pollutant','PM2.5 (tons)','PM2.5 Gasoline'            ): -487200.0,
    ('Air Pollutant','PM2.5 (tons)','PM2.5 Diesel'              ): -490300.0,
    ('Air Pollutant','CO2 (metric tons)','CO2'                  ):     -55.35,
    ('Air Pollutant','Other (tons)','NOX'                       ):   -7800.0,
    ('Air Pollutant','Other (tons)','SO2'                       ):  -40500.0,
    ('Air Pollutant','Volatile Organic Compounds (metric tons)','Acetaldehyde' ):  -5700,
    ('Air Pollutant','Volatile Organic Compounds (metric tons)','Benzene'      ): -12800,
    ('Air Pollutant','Volatile Organic Compounds (metric tons)','1,3-Butadiene'): -32200,
    ('Air Pollutant','Volatile Organic Compounds (metric tons)','Formaldehyde' ):  -6400,
    ('Air Pollutant','Volatile Organic Compounds (metric tons)','All other VOC'):  -5100,
    ('Collisions & Active Transport','Fatalies due to Collisions'): -4590000,
    ('Collisions & Active Transport','Injuries due to Collisions'):   -64400,
    ('Collisions & Active Transport','Property Damage Only (PDO) Collisions'): -2455,
    ('Collisions & Active Transport','Active Individuals'        ):     1220,
    }

    def __init__(self, rundir, read_base=True):
        """
    Parameters
    ----------
    rundir : string
        The directory containing the raw output for the model run.
    read_base : bool
        Pass true if we should create another instance of this class to read the output
        of a base directory.
    """
        # read the configs
        self.rundir = rundir
        config_file = os.path.join(rundir, "BC_config.csv")
        self.config = pd.Series.from_csv(config_file, header=None, index_col=0)

        # Make sure required values are in the configuration
        print("Reading result csvs from '%s'" % self.rundir)
        try:
            for key in RunResults.REQUIRED_KEYS:
                print("  %16s '%s'" % (key, self.config.loc[key]))

        except KeyError as e:
            print("Configuration file %s missing required variable: %s" % (config_file, str(e)))
            sys.exit(2)

        # Not required
        self.base_dir     = None
        self.base_results = None
        if read_base:
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
            self.base_results = RunResults(rundir = self.base_dir, read_base=False) # don't recursive loop
            self.base_results.calculateDailyMetrics()

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

        self.transit_boards_miles = \
            pd.read_table(os.path.join(self.rundir, "transit_boards_miles.csv"),
                          sep=",", index_col=0)
        # print self.transit_boards_miles

        self.transit_times_by_acc_mode_egr = \
            pd.read_table(os.path.join(self.rundir, "transit_times_by_acc_mode_egr.csv"),
                          sep=",", index_col=[0,1,2])
        # print self.transit_times_by_acc_mode_egr

        self.transit_times_by_mode_income = \
            pd.read_table(os.path.join(self.rundir, "transit_times_by_mode_income.csv"),
                          sep=",", index_col=[0,1])
        # print self.transit_times_by_mode_income

    def calculateDailyMetrics(self):
        """
        Calculates the daily output metrics which will actually get used for the benefits/cost
        analysis.
        """
        # we really want these by class -- ignore time periods and income levels
        vmt_byclass     = self.vmt_vht_metrics.sum(level='vehicle class') # vehicles, not people
        transit_byclass = self.transit_times_by_acc_mode_egr.sum(level='Mode')
        nonmot_byclass  = self.nonmot_times.sum(level='Mode')             # person trips
        auto_byclass    = self.auto_times.sum(level='Mode')               # person trips

        daily_results   = collections.OrderedDict()

        ######################################################################################
        cat1            = 'Travel Time'
        cat2            = 'Auto/Truck (Hours)'
        daily_results[(cat1,cat2,'SOV (PHT)'  )] = vmt_byclass.loc[['DA','DAT'],'VHT'].sum()
        daily_results[(cat1,cat2,'HOV2 (PHT)' )] = vmt_byclass.loc[['S2','S2T'],'VHT'].sum()*2
        daily_results[(cat1,cat2,'HOV3+ (PHT)')] = vmt_byclass.loc[['S3','S3T'],'VHT'].sum()*3.5
        daily_results[(cat1,cat2,'Truck (VHT)')] = vmt_byclass.loc[['SM','SMT','HV','HVT'],'VHT'].sum()

        # TODO: These are vehicle hours, I think.  Why not make them person hours?
        cat2            = 'Non-Recurring Freeway Delay (Hours)'
        daily_results[(cat1,cat2,'Auto' )] = \
            vmt_byclass.loc[['DA','DAT','S2','S2T','S3','S3T'],'Non-Recurring Freeway Delay'].sum()
        daily_results[(cat1,cat2,'Truck')] = \
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
        # TODO: What's the "OVTT Adjustment (Total Trips)"  ?

        cat2            = 'Walk/Bike (Hours)'
        daily_results[(cat1,cat2,'Walk')] = nonmot_byclass.loc['Walk','Total Time (Hours)']
        daily_results[(cat1,cat2,'Bike')] = nonmot_byclass.loc['Bike','Total Time (Hours)']

        ######################################################################################
        cat1            = 'Travel Cost'
        cat2            = 'VMT'
        daily_results[(cat1,cat2,'Auto' )] = \
            vmt_byclass.loc[['DA','DAT','S2','S2T','S3','S3T'],'VMT'].sum()        
        daily_results[(cat1,cat2,'Truck')] = \
            vmt_byclass.loc[['SM','SMT','HV','HVT'],'VMT'].sum()

        # Vehicles Owned
        cat2            = 'Vehicle Ownership'
        daily_results[(cat1,cat2,'All Income Quartiles')] = self.autos_owned['total autos'].sum()

        # Parking
        cat2            = 'Auto Trips'
        daily_results[(cat1,cat2,'SOV'  )] = auto_byclass.loc[['da' ,'datoll' ],'Daily Trips'].sum()
        daily_results[(cat1,cat2,'HOV2' )] = auto_byclass.loc[['sr2','sr2toll'],'Daily Trips'].sum()/2.0
        daily_results[(cat1,cat2,'HOV3+')] = auto_byclass.loc[['sr3','sr3toll'],'Daily Trips'].sum()/3.5
        total_autotrips = daily_results[(cat1,cat2,'SOV')] + daily_results[(cat1,cat2,'HOV2')] + daily_results[(cat1,cat2,'HOV3+')]
        cat2            = 'Trips with Parking Costs'
        daily_results[(cat1,cat2,'Work'    )] = total_autotrips * RunResults.PERCENT_PARKING_NONHOME * RunResults.PERCENT_PARKING_WORK
        daily_results[(cat1,cat2,'Non-Work')] = total_autotrips * RunResults.PERCENT_PARKING_NONHOME * (1.0-RunResults.PERCENT_PARKING_WORK)

        ######################################################################################
        cat1            = 'Air Pollutant'
        cat2            = 'PM2.5 (tons)'
        daily_results[(cat1,cat2,'PM2.5 Gasoline')] = \
            vmt_byclass.loc[:,'Gas_PM2.5'].sum()*RunResults.EMISSIONS_SCALEUP + \
            (daily_results[('Travel Cost','VMT','Auto')]*(RunResults.PM25_MAGIC_A+RunResults.PM25_MAGIC_B)*RunResults.PM25_MAGIC_C)
        daily_results[(cat1,cat2,'PM2.5 Diesel'  )] = \
            vmt_byclass.loc[:,'Diesel_PM2.5'].sum()*RunResults.EMISSIONS_SCALEUP + \
            (daily_results[('Travel Cost','VMT','Truck')]*(RunResults.PM25_MAGIC_A+RunResults.PM25_MAGIC_B)*RunResults.PM25_MAGIC_C)

        cat2            = 'CO2 (metric tons)'
        daily_results[(cat1,cat2,'CO2')] = vmt_byclass.loc[:,'CO2'  ].sum()

        cat2            = 'Other (tons)'
        daily_results[(cat1,cat2,'NOX')] = vmt_byclass.loc[:,'S_NOx'].sum()*RunResults.EMISSIONS_SCALEUP
        daily_results[(cat1,cat2,'SO2')] = vmt_byclass.loc[:,'SOx'  ].sum()*RunResults.EMISSIONS_SCALEUP

        # http://en.wikipedia.org/wiki/Volatile_organic_compound
        cat2            = 'Volatile Organic Compounds (metric tons)'
        daily_results[(cat1,cat2,'Acetaldehyde' )] = vmt_byclass.loc[:,'Acetaldehyde'  ].sum()*RunResults.EMISSIONS_SCALEUP
        daily_results[(cat1,cat2,'Benzene'      )] = vmt_byclass.loc[:,'Benzene'       ].sum()*RunResults.EMISSIONS_SCALEUP
        daily_results[(cat1,cat2,'1,3-Butadiene')] = vmt_byclass.loc[:,'Butadiene'     ].sum()*RunResults.EMISSIONS_SCALEUP
        daily_results[(cat1,cat2,'Formaldehyde' )] = vmt_byclass.loc[:,'Formaldehyde'  ].sum()*RunResults.EMISSIONS_SCALEUP
        daily_results[(cat1,cat2,'All other VOC')] = vmt_byclass.loc[:,'ROG'].sum()*RunResults.EMISSIONS_SCALEUP \
            - daily_results[(cat1,cat2,'Acetaldehyde' )] \
            - daily_results[(cat1,cat2,'Benzene'      )] \
            - daily_results[(cat1,cat2,'1,3-Butadiene')] \
            - daily_results[(cat1,cat2,'Formaldehyde' )]

        ######################################################################################
        cat1            = 'Collisions & Active Transport'
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

        cat2         = 'Avg Minutes Active Tranport per Person'
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

    def calculateBenefitCosts(self, BC_detail_workbook, all_projects_dir):
        """
        Compares the run results with those from the base results (if they exist),
        calculating the daily difference, annual difference, and annual benefits.

        Writes a readable version into `BC_detail_workbook`, and flat csv series
        into a csv in `all_projects_dir` named [Project ID].csv.
        """
        # these will be the daily and annual diffs, and monetized diffs
        # key = (category1, category2, variable name)
        bc_metrics      = collections.OrderedDict()
        # put config in here first
        for key,val in self.config.iteritems():
            bc_metrics[(key,"","")] = val

        workbook        = xlsxwriter.Workbook(BC_detail_workbook)
        worksheet       = workbook.add_worksheet('project')
        worksheet.protect()

        # Notice row
        format_red      = workbook.add_format({'font_color':'red'})
        worksheet.write(0,0, "This workbook is written by the script %s.  " % os.path.realpath(__file__) + 
                             "DO NOT CHANGE THE WORKBOOK, CHANGE THE SCRIPT.",
                             format_red)
        # Info rows
        format_label    = workbook.add_format({'align':'right','indent':1})
        format_highlight= workbook.add_format({'bg_color':'yellow'})
        format_highlight_money = workbook.add_format({'bg_color':'yellow',
                                                     'num_format':'_($* #,##0_);_($* (#,##0);_($* "-"_);_(@_)'})

        worksheet.write(1,0, "Project Run Dir", format_label)
        worksheet.write(1,1, os.path.realpath(self.rundir), format_highlight)
        for col in range(2,7): worksheet.write(1,col,"",format_highlight)

        row = 2
        for key in RunResults.REQUIRED_KEYS:
            worksheet.write(row,0, key, format_label)
            worksheet.write(row,1, self.config.loc[key], 
                            format_highlight_money if string.find(key,'Costs') >= 0 else format_highlight)
            for col in range(2,7): worksheet.write(row,col,"",format_highlight)


        if self.base_dir:
            worksheet.write(8,0, "Base Run Dir", format_label)
            worksheet.write(8,1, self.base_dir, format_highlight)
            for col in range(2,7): worksheet.write(8,col,"",format_highlight)

        # Header row
        row  = 10
        format_header = workbook.add_format({'bg_color':'#1F497D',
                                             'font_color':'white',
                                             'bold':True,
                                             'text_wrap':True,
                                             'align':'center'})
        worksheet.write(row,0,"Benefit/Cost",format_header)
        worksheet.write(row,1,"Daily\nWith Project" if self.base_dir else "Daily",format_header)
        if self.base_dir:
            worksheet.write(row,2,"Daily\nNo Build",format_header)
            worksheet.write(row,3,"Daily\nDifference",format_header)
            worksheet.write(row,4,"Annual\nDifference",format_header)
            worksheet.write(row,6,"Benefit Valuation\n(per unit)",format_header)
            worksheet.write(row,8,"Annual\nBenefit ($2013)",format_header)

        # Data rows
        row  += 1
        cat1 = None
        cat2 = None
        format_cat1     = workbook.add_format({'bold':True, 'bg_color':'#C5D9F1'})
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

        for key,value in self.daily_results.iteritems():

            # What's the valuation of this metric?
            valuation = 0
            if (key[0],key[1],key[2]) in RunResults.BENEFIT_VALUATION:
                valuation = RunResults.BENEFIT_VALUATION[(key[0],key[1],key[2])]
            elif (key[0],key[1]) in RunResults.BENEFIT_VALUATION:
                valuation = RunResults.BENEFIT_VALUATION[(key[0],key[1])]
            else:
                # these are purely informational
                print("Could not lookup benefit valuation for %s" % str(key))

            # is this already annual?  (e.g. no daily -> annual transformation)
            already_annual = False
            if (key[0],key[1],key[2]) in RunResults.ALREADY_ANNUAL:
                already_annual = RunResults.ALREADY_ANNUAL[(key[0],key[1],key[2])]
            elif (key[0],key[1]) in RunResults.ALREADY_ANNUAL:
                already_annual = RunResults.ALREADY_ANNUAL[(key[0],key[1])]

            # category one header
            if cat1 != key[0]:
                cat1 = key[0]
                worksheet.write(row,0,cat1,format_cat1)
                worksheet.write(row,1,"",format_cat1)
                if self.base_dir:
                    worksheet.write(row,2,"",format_cat1)
                    worksheet.write(row,3,"",format_cat1)
                    worksheet.write(row,4,"",format_cat1)
                    worksheet.write(row,5,"",format_cat1)
                    worksheet.write(row,6,"",format_cat1)
                    worksheet.write(row,7,"",format_cat1)
                    worksheet.write(row,8,"",format_cat1)
                row += 1

            # category two header
            if cat2 != key[1]:
                cat2 = key[1]
                worksheet.write(row,0,cat2,format_cat2)
                # Sum it
                worksheet.write(row,1,
                                '=SUM(%s)' % xl_range(row+1,1,row+len(self.daily_results[cat1][cat2]),1),
                                format_cat2_lil if (cat1,cat2) in self.lil_cats else format_cat2_big)
                if self.base_dir:
                    worksheet.write(row,2, # base
                                    '=SUM(%s)' % xl_range(row+1,2,row+len(self.daily_results[cat1][cat2]),2),
                                    format_cat2b_lil if (cat1,cat2) in self.lil_cats else format_cat2b_big)

                    if already_annual:
                        worksheet.write(row,3, # diff daily
                                        "",
                                        format_cat2d_lil if (cat1,cat2) in self.lil_cats else format_cat2d_big)
                        worksheet.write(row,4, # diff annual
                                        '=%s-%s' % (xl_rowcol_to_cell(row,1), xl_rowcol_to_cell(row,2)),
                                        format_cat2d_lil if (cat1,cat2) in self.lil_cats else format_cat2d_big)
    
                        bc_metrics[(cat1,cat2,'Difference')] = self.daily_category_results[(cat1,cat2)] - \
                                                               self.base_results.daily_category_results[(cat1,cat2)]
                    else:
                        worksheet.write(row,3, # diff daily
                                        '=%s-%s' % (xl_rowcol_to_cell(row,1), xl_rowcol_to_cell(row,2)),
                                        format_cat2d_lil if (cat1,cat2) in self.lil_cats else format_cat2d_big)
                        worksheet.write(row,4, # diff annual
                                        '=%d*%s' % (RunResults.ANNUALIZATION, xl_rowcol_to_cell(row,3)),
                                        format_cat2d_lil if (cat1,cat2) in self.lil_cats else format_cat2d_big)

                        bc_metrics[(cat1,cat2,'Daily Difference')] = self.daily_category_results[(cat1,cat2)] - \
                                                                     self.base_results.daily_category_results[(cat1,cat2)]
                        bc_metrics[(cat1,cat2,'Annual Difference')] = RunResults.ANNUALIZATION * \
                                                                      bc_metrics[(cat1,cat2,'Daily Difference')]


                    # worksheet.write(row,6, "", format_cat2d_lil)    

                    if valuation != 0:
                        worksheet.write(row,8,
                                        '=SUM(%s)' % xl_range(row+1,8,row+len(self.daily_results[cat1][cat2]),8),
                                        format_cat2_ben)
                row += 1

            # details
            worksheet.write(row,0,key[2],format_var)
            worksheet.write(row,1,value,
                            format_val_lil if (cat1,cat2) in self.lil_cats else format_val_big)
            if self.base_dir:
                worksheet.write(row,2, # base
                                self.base_results.daily_results[cat1][cat2][key[2]],
                                format_val_lil if (cat1,cat2) in self.lil_cats else format_val_big)
                nominal_diff = 0
                if already_annual:
                    worksheet.write(row,4, # diff annual
                                    '=%s-%s' % (xl_rowcol_to_cell(row,1), xl_rowcol_to_cell(row,2)),
                                    format_val_lil if (cat1,cat2) in self.lil_cats else format_val_big)
                    nominal_diff = self.daily_results[cat1][cat2][key[2]] - \
                                   self.base_results.daily_results[cat1][cat2][key[2]]
                else:
                    worksheet.write(row,3, # diff daily
                                    '=%s-%s' % (xl_rowcol_to_cell(row,1), xl_rowcol_to_cell(row,2)),
                                    format_val_lil if (cat1,cat2) in self.lil_cats else format_val_big)
                    worksheet.write(row,4, # diff annual
                                    '=%d*%s' % (RunResults.ANNUALIZATION, xl_rowcol_to_cell(row,3)),
                                    format_val_lil if (cat1,cat2) in self.lil_cats else format_val_big)
                    nominal_diff = RunResults.ANNUALIZATION * (self.daily_results[cat1][cat2][key[2]] - \
                                                               self.base_results.daily_results[cat1][cat2][key[2]])

                if valuation != 0:
                    worksheet.write(row,6, # diff annual
                                    valuation,
                                    format_benval_lil if abs(valuation)<1000 else format_benval_big)
                    worksheet.write(row,8, # annual benefit
                                    '=%s*%s' % (xl_rowcol_to_cell(row,4), xl_rowcol_to_cell(row,6)),
                                    format_ann_ben)
                    if (cat1,cat2,'Annual Benefit ($2013)') not in bc_metrics:
                        bc_metrics[(cat1,cat2,'Annual Benefit ($2013)')] = 0
                    bc_metrics[(cat1,cat2,'Annual Benefit ($2013)')] += valuation*nominal_diff

            row += 1

        worksheet.set_column(0,0,40.0)
        worksheet.set_column(1,8,13.0)
        worksheet.set_column(5,5,2.0)
        worksheet.set_column(7,7,2.0)
        workbook.close()
        print("Wrote %s" % BC_detail_workbook)

        if self.base_dir:
            idx = pd.MultiIndex.from_tuples(bc_metrics.keys(), 
                                            names=['category1','category2','variable_name'])
            self.bc_metrics = pd.Series(bc_metrics, index=idx)
            self.bc_metrics.name = 'values'
 
            all_proj_filename = os.path.join(all_projects_dir, "%s.csv" % self.config.loc['Project ID'])
            self.bc_metrics.to_csv(all_proj_filename, header=True)
            print("Wrote %s" % all_proj_filename)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(usage=USAGE)
    parser.add_argument('project_dir',
                        help="The directory with the run results csvs.")
    parser.add_argument('all_projects_dir',
                        help="The directory in which to write the Benefit/Cost summary Series")
    args = parser.parse_args(sys.argv[1:])

    rr = RunResults(args.project_dir)
    rr.calculateDailyMetrics()

    rr.calculateBenefitCosts(os.path.join(args.project_dir, "BC.xlsx"),
                             args.all_projects_dir)
