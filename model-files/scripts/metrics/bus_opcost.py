import numpy
import os
import pandas
import re
import xlrd

USAGE = """
 python bus_opcost.py

 Reads trn/trnline[am|md|pm|ev|ea]_wlk_com_wlk.csv

 - Sums the vehicle miles to the operator (based on the number code)
 - Multiplies by Local Streets Roads (vs hwy) and county assumptions for that operator
   (assumptins in INPUTS\metrics\Transit Operator LSR VMT Estimates.xlsx)
 - Multiplies by Operating Costs for buses
 
 Outputs a sum of bus VMT on Local Streets and Roads by county into 

   metrics\bus_opcost.csv

 """


TRNLINE_HEADER = ["name","mode","owner","frequency","line time","line dist","total boardings","passenger miles","passenger hours","path id"]

EFFECTIVE_TRN_HOURS = {'timeperiod': ['ea','am','md','pm','ev'],
                       'effective hours':[2,4,5,4,4]}

# mapping from transit operator -> pct route VMT on local streets, pct route VMT in each county
TRN_MAPPING_FILE = os.path.join("INPUT","metrics","Transit Operator LSR VMT Estimates.xlsx")

BUS_OPCOST_FILE  = os.path.join("INPUT","sgr","PavementCosts.block")

OUTFILE          = os.path.join("metrics", "bus_opcost.csv")

COUNTY_ABBREVS = {
  'ALA':'Alameda',
  'CC' :'Contra Costa',
  'MRN':'Marin',
  'NAP':'Napa',
  'SF' :'San Francisco',
  'SM' :'San Mateo',
  'SCL':'Santa Clara',
  'SOL':'Solano',
  'SON':'Sonoma'
}

def read_pavement_costs():
    """
    Read the pavement cost config file.
    Returns a dictionary with variables.
    """
    IGNORE_re   = r"^((\s*)|(\s*;.*))$"  # whitespace or comment (with optional preceding whitespace)
    VAR_re      = r"^(\S+)\s*=\s*(\S+)"  # X = Y
    returndict  = {}
    f = open(BUS_OPCOST_FILE,'r')
    for line in f:
        line = line.strip()
        if re.match(IGNORE_re, line):
            # print "Ignoring [%s]" % line
            continue
        m = re.match(VAR_re, line)
        if m == None:
            print "Don't understand line [%s] in %s" % (line, BUS_OPCOST_FILE)
            raise

        returndict[m.group(1)] = float(m.group(2))
    f.close()
    return returndict

if __name__ == '__main__':

    # collect the data in here
    full_table_df = None
    set_fulltable = False

    for timeperiod in ['ea','am','md','pm','ev']:
        # we only need to read wlk_com_wlk because every line is there
        filename = os.path.join("trn", "trnline%s_wlk_com_wlk.csv" % timeperiod)
        temp_df = pandas.read_csv( filename, names=TRNLINE_HEADER)

        if set_fulltable==False: # it doesn't like checking if a dataFrame is none
            full_table_df = temp_df
            set_fulltable = True
        else:
            full_table_df = full_table_df.append(temp_df)

        print "Read %6d lines from %s; total lines = %6d" % (len(temp_df), filename, len(full_table_df))

    # setup timeperiod
    full_table_df['timeperiod'] = full_table_df['path id'].str.extract('^(..)')
    # effective hours for that timeperiod
    full_table_df = pandas.merge(full_table_df, pandas.DataFrame(EFFECTIVE_TRN_HOURS), how='left')

    # set up operator id
    full_table_df['operator'] = full_table_df['name'].str.extract('^(\d+)_')
    full_table_df['operator'] = full_table_df['operator'].apply(int)

    # route speed (miles per hour)
    full_table_df['route speed'] = 60.0*full_table_df['line dist']/full_table_df['line time']
    # route vehicles (vehicle hours)
    full_table_df['route vehicles'] = numpy.ceil(full_table_df['line time']/full_table_df['frequency'])
    # route VMT per hour = vehicle hours * miles/hour
    full_table_df['route VMT per hour'] = full_table_df['route speed']*full_table_df['route vehicles']
    # route VMT = route VMT per hour * effective hours per time period
    full_table_df['route VMT'] = full_table_df['route VMT per hour']*full_table_df['effective hours']

    # sum VMT to operator id
    route_vmt = full_table_df.groupby('operator').sum()['route VMT']
    # print route_vmt

    # read mapping
    excel_mapping = xlrd.open_workbook(TRN_MAPPING_FILE,encoding_override="cp1252")
    transit_op_mapping = pandas.io.excel.read_excel(TRN_MAPPING_FILE,header=1)
    transit_op_mapping.rename(columns={'#':'operator','Operator':'Operator Description'}, inplace=True)
    transit_op_mapping = transit_op_mapping.set_index('operator')
    # print transit_op_mapping

    # read opcost config
    pvcosts = read_pavement_costs()

    # join it to route_vmt
    route_vmt = pandas.DataFrame({'route vmt':route_vmt})
    route_vmt = pandas.concat([route_vmt, transit_op_mapping], axis=1)

    route_vmt_by_county = {}
    opcost_base_by_county = {}
    opcost_mult_by_county = {}
    # sum up to county
    for abbrev,county in COUNTY_ABBREVS.iteritems():
        route_vmt[county] = route_vmt['route vmt']*route_vmt[abbrev]*route_vmt['LSR']
        route_vmt_by_county[county] = route_vmt[county].sum()
        opcost_base_by_county[county] = pvcosts['BUSOOPCOST']
        opcost_mult_by_county[county] = 1 + pvcosts['%s_BUS_PAVE' % abbrev]

    # make it a dataframe
    by_county = pandas.DataFrame([route_vmt_by_county, 
                                  opcost_base_by_county,
                                  opcost_mult_by_county])
    by_county = by_county.transpose()
    by_county.rename(columns={0:'route vmt',
                              1:'base opcost per mile',
                              2:'pct opcost change'}, inplace=True)
    # in year 2000 cents, because BUSOPCOST is in year 2000 cents
    by_county['opcost per mile'] = by_county['base opcost per mile']*by_county['pct opcost change']

    # in year 2000 dollars
    by_county['opcost'] = by_county['route vmt']*by_county['opcost per mile']*0.01
    by_county.index.names = ['county']

    by_county.to_csv(OUTFILE)
    print "Wrote %s" % OUTFILE

