import argparse, itertools, optparse, os, sys
import numpy, pandas

USAGE = """
  python hwynet.py --filter filter --year 2035 hwy\\iter3\\avgload5period_vehclasses.csv [--link_mapping links_mapping.csv indexcol sharecol output_suffix]

 Reads the csv file of links from hwynet.csv and reports a number of
 metrics into metrics/vmt_vht_metrics by timeperiod and vehicle class.

 Also reads 
   - INPUT\\metrics\\nonRecurringDelayLookup.csv
   - INPUT\\metrics\\collisionLookup.csv
   - INPUT\\metrics\\emissionsLookup.csv

 These metrics consist of the following:
  * VMT: Vehicle Miles Traveled
  * VHT: Vehicle Hours Traveled
  * Hypothetical Freeflow Time: VHT if all vehicles traveled at freeflow speed
 -- Using nonRecurringDelayLookup.csv
  * Non-Recurring Freeway Delay: estimated delay experienced on freeway links that is non-recurring.
 -- Using collisionLookup.csv
  * Motor Vehicle Fatality
  * Motor Vehicle Injury
  * Motor Vehicle Property
  * Walk Fatality
  * Walk Injury
  * Bike Fatality
  * Bike Injury
 -- Using emissionsLookup.csv
  * ROG
  * S_NOx
  * SOx
  * W_NOx
  * CO2
  * Diesel_PM2.5
  * Gas_PM2.5
  * Diesel PM
  * Butadiene
  * Benzene
  * Acetaldehyde
  * Formaldehyde
  * TOG_exh
  * PM10
  * PM10_wear
  * PM2.5_wear

  If optional --link_mapping parameters are specified (--link_mapping links_mapping.csv indexcol sharecol output_suffix), then
  links_mapping.csv is read and columns [A,B,(indexcol),(sharecol)] are read and assumed to cover all the links.
  The per-link metric values are then joined to this dataframe by A,B and multiplied by sharecol and aggregated by indexcol.
  The script will then output the additional file, metrics\\vmt_vht_metrics(output_suffix).csv

  This file additionally has two more columns:
  * road_type: 'freeway' for facility type (ft) in [1,2,3,8], 'non-freeway' otherwise
  * area_type: 'urban' for area type (at) <= 3, 'suburban' for area type == 4, 'rural' for area type == 5

  For example, to get vmt_vht_metrics by TAZ, create a link-to-TAZ mapping file as follows:

  1) From a directory with the shapefile export of the roadway network 
     e.g. M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT\Networks\BlueprintNetworks_50\\net_2050_Blueprint Plus Crossing\shapefile
      
     Run the following command:
     python X:\\travel-model-one-master\utilities\cube-to-shapefile\correspond_link_to_TAZ.py network_links.shp network_links_TAZ.csv

     This will create a file with columns A, B, TAZ1454, link_mi, linktaz_mi, linktaz_share

     Here, the indexcol is TAZ1454, and the sharecol is linktaz_share

  2) Then run this script with the --link_mapping args as follows:

    e.g. python X:\\travel-model-one-master\utilities\RTP\metrics\hwynet.py --filter PBA50 --year 2035 
         --link_mapping "M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT\Networks\BlueprintNetworks_51\\net_2035_Blueprint Plus\shapefile\\network_links_TAZ.csv" TAZ1454 linktaz_share _by_taz
         hwy\iter3\\avgload5period_vehclasses.csv 

"""
pandas.options.display.width = 1000
pandas.options.display.max_columns = 100

parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
parser.add_argument("--filter", metavar="lookup_filter", help="Filter keyword for lookup files", required=True)
parser.add_argument("--year",   metavar="year", help="Filter keyword for lookup files", required=True, type=int)
parser.add_argument("net_csv",  metavar="avgload5period_vehclasses.csv", help="Loaded network export with vehicle classes")
parser.add_argument("--link_mapping", metavar="link_mapping",  nargs=4,
                    help="Optional mapping csv to summarize by another index. Four args are: links_mapping.csv indexcol sharecol output_suffix")

args = parser.parse_args()
datafile            = args.net_csv
lookupdir           = os.path.join( "INPUT","metrics" )
vmt_vht_outputfile  = os.path.join("metrics", "vmt_vht_metrics.csv")
vclasses            = ['DA',  'S2',  'S3', 'SM', 'HV',
                       'DAT', 'S2T', 'S3T','SMT','HVT',
                       'DAAV','S2AV','S3AV']

vclassgroup         = {'DA':'auto',  'DAT':'auto', 'DAAV':'auto', # use for emissions
                       'S2':'auto',  'S2T':'auto', 'S2AV':'auto',
                       'S3':'auto',  'S3T':'auto', 'S3AV':'auto',
                       'SM':'SM',    'SMT':'SM',
                       'HV':'HV',    'HVT':'HV'}
periods             = ['EA','AM','MD','PM','EV']

# Read the link data
link_df = pandas.read_csv(datafile)
num_links = len(link_df)
print("Read {} links from {}".format(num_links, datafile))
id_fields    = ['a','b']
fields       = ['distance','lanes','at','ft','fft']

link_mapping_df = pandas.DataFrame()
if args.link_mapping:
  link_mapping_df = pandas.read_csv(args.link_mapping[0])
  # keep A,B,[indexcol],[sharecol]
  link_mapping_df = link_mapping_df[[ 'A','B',args.link_mapping[1], args.link_mapping[2] ]]
  # rename A,B to a,b
  link_mapping_df.rename(columns={'A':'a','B':'b'}, inplace=True)
  print("link_mapping_df read from {}; head:\n{}".format(args.link_mapping[0], link_mapping_df.head()))
  print("link_mapping_df.{}.sum()={}".format(args.link_mapping[2], link_mapping_df[args.link_mapping[2]].sum()))

# first, unstack timeperiod fields - so instead of xxEA, xxAM, xxMD, etc, we have xx with timeperiod as a column
# so this will be link_df x 5
link_tp_df = pandas.DataFrame()
for tp_field in ['cspd{}','vol{}_tot','vc{}','ctim{}']:
    tp_field_list = list(tp_field.format(tp) for tp in periods)
    tp_field_df   = pandas.DataFrame({'timeperiod':periods, 'variable':tp_field_list})

    # this will result in columns variable (with values xxEA etc) and value
    melted_df = pandas.melt(link_df, id_vars=id_fields, value_vars=tp_field_list)
    # add timeperiod field and rename value to tp_field without '{}', drop variable col
    melted_df = pandas.merge(how='left', left=melted_df, right=tp_field_df)
    melted_df.rename(columns={'value':tp_field.replace('{}','')}, inplace=True)
    melted_df.drop(columns=['variable'], inplace=True)
    # now we have id_fields, xx, timeperiod -- join up
    if len(link_tp_df) == 0:
        link_tp_df = melted_df
    else:
        link_tp_df = pandas.merge(left=link_tp_df, right=melted_df, how='left')

# add in other link-specific non-id fields
link_tp_df = pandas.merge(how='left', left=link_tp_df, right=link_df[id_fields + fields], on=id_fields)
print("Melted to timeperiods to create link_tp_df: {} rows".format(len(link_tp_df)))
print(link_tp_df.head())
assert(len(link_tp_df) == len(periods)*num_links)

# unstack so that timeperiods and vehicle classes are a column
# first create a variable name decoder DF with timeperiod, vclass, variable
timeperiod_list  = []
vclass_list      = []
tp_vc_field_list = []
for x in itertools.product(periods, vclasses):
    timeperiod_list.append(x[0])
    vclass_list.append(x[1].lower())
    tp_vc_field_list.append('vol{}_{}'.format(x[0],x[1].lower()))

tp_vc_field_df = pandas.DataFrame({'timeperiod':timeperiod_list, 'vclass':vclass_list, 'variable':tp_vc_field_list})

# do the melt and join with our decoder
link_tp_vehclass_df = pandas.melt(link_df, id_vars=id_fields, value_vars=tp_vc_field_list)
link_tp_vehclass_df = pandas.merge(how='left', left=link_tp_vehclass_df, right=tp_vc_field_df)
link_tp_vehclass_df = link_tp_vehclass_df.rename(columns={'value':'vol'}).drop(columns='variable')
print("Melted to timeperiods x vehclasses to createlink_tp_vehclass_df: {} rows".format(len(link_tp_vehclass_df)))
print(link_tp_vehclass_df.head())
assert(len(link_tp_vehclass_df) == len(vclasses)*len(periods)*num_links)

# units: Hours delay per VMT
# Map headers -> index for this lookup and read lookup data
nrc_file = os.path.join(lookupdir,"nonRecurringDelayLookup.csv")
nrclookup_df = pandas.read_csv(nrc_file)
# filter by given filter
nrclookup_df = nrclookup_df.loc[ (nrclookup_df['filter'] == args.filter)&
                                 (nrclookup_df['year']   == args.year  ) ].copy()
nrclookup_df['vcratio'] = nrclookup_df['vcratio'].map('{:,.2f}'.format) # convert to string with two decimals

if len(nrclookup_df) == 0:
  print("No nonRecurringDelay lookups for {} found".format(args.filter))
  sys.exit(2)
nrclookup_df.drop(columns=['filter','year'],inplace=True)

# transform so columns are: vcratio (str), lanes_24(int), nrcdelay (float)
nrclookup_df.set_index('vcratio',inplace=True)
nrclookup_df.rename(columns={'2lanes':2, '3lanes':3, '4lanes':4}, inplace=True)
nrclookup_df = nrclookup_df.stack().reset_index().rename(columns={'level_1':'lanes_24',0:'nrcdelay'})
print(nrclookup_df.head())
print("Read {} and filtered by {} and year {} to create nrclookup_df:\n{}".format(nrc_file, args.filter, args.year, nrclookup_df.head()))

# Units are collisions per 1,000,000 VMT
# Map headers -> index for this lokup and read lookup data
collision_file = os.path.join(lookupdir,"collisionLookup.csv")
collisionlookup_df = pandas.read_csv(collision_file)
collision_types = list(collisionlookup_df.columns.values)
collision_types.remove('ft')
collision_types.remove('at')
collision_types.remove('filter')
collision_types.remove('year')
# filter by given filter
collisionlookup_df = collisionlookup_df.loc[ (collisionlookup_df['filter'] == args.filter)&
                                             (collisionlookup_df['year'  ] == args.year  ) ].copy()
if len(collisionlookup_df) == 0:
  print("No collisions lookups for {} found".format(args.filter))
  sys.exit(2)
collisionlookup_df.drop(columns=['filter','year'],inplace=True)
print("Read {} and filtered by {} and year {} to create collisionlookup_df:\n{}".format(collision_file, args.filter, args.year, collisionlookup_df.head()))

# Units are grams per mile (equivalent to metric tons per 1,000,000 VMT)
emission_file = os.path.join(lookupdir,"emissionsLookup.csv")
emissionslookup_df = pandas.DataFrame()
if not os.path.exists(emission_file):
  print("Emissions file {} doesn't exist -- skipping".format(emission_file))
else:
  emissionslookup_df = pandas.read_csv(emission_file)
  emission_types = list(emissionslookup_df.columns.values)
  emission_types.remove('period')
  emission_types.remove('vclassgroup')
  emission_types.remove('speed')
  emission_types.remove('filter')
  emission_types.remove('year')
  # filter by given filter
  emissionslookup_df = emissionslookup_df.loc[ (emissionslookup_df['filter'] == args.filter)&
                                               (emissionslookup_df['year'  ] == args.year  ) ].copy()
  if len(emissionslookup_df) == 0:
    print("No emission lookups for {} found".format(args.filter))
    sys.exit(2)
  emissionslookup_df.drop(columns=['filter','year'],inplace=True)
  print("Read {} and filtered by {} and year {} to create emissionslookup_df:\n{}".format(emission_file, args.filter, args.year, emissionslookup_df.head()))

# Add link x timeperiod columns

# lanes_24 is lanes but capped in [2,4]
link_tp_df['lanes_24'] = link_tp_df['lanes']
link_tp_df.loc[ link_tp_df.lanes_24 < 2, 'lanes_24' ] = 2
link_tp_df.loc[ link_tp_df.lanes_24 > 4, 'lanes_24' ] = 4

# vcratio is used to lookup non-recurring delay; string version, capped at 1
link_tp_df['vcratio'] = link_tp_df['vc']                         # start with VC
link_tp_df.loc[ link_tp_df.vcratio > 1.0, 'vcratio' ] = 1.0      # cap it at 1.0
link_tp_df['vcratio'] = link_tp_df['vcratio'].map('{:,.2f}'.format) # convert to string with two decimals

# join to get non recurring delay per vmt lookup
link_tp_df = pandas.merge(left    = link_tp_df,
                          right   = nrclookup_df,
                          on      = ['vcratio', 'lanes_24']).rename(columns={'nrcdelay':'nrcdelay_pervmt'})
print("a link_tp_df len {}:\n{}".format(len(link_tp_df), link_tp_df.head()))
assert(len(link_tp_df) == len(periods)*num_links)

# for collision lookup
link_tp_df['collision_ft'] = link_tp_df['ft']
link_tp_df.loc[ link_tp_df.ft == 1,          'collision_ft'] =  2 # Freeway-to-freeway connector is like a freeway
link_tp_df.loc[ link_tp_df.ft == 8,          'collision_ft'] =  2 # managed freeway is like a freeway
link_tp_df.loc[ link_tp_df.ft == 6,          'collision_ft'] = -1 # skip dummy links
link_tp_df.loc[ link_tp_df.lanes <= 0,       'collision_ft'] = -1 # or those with lanes <= 0
link_tp_df.loc[ link_tp_df.collision_ft > 4, 'collision_ft'] = 4 # cap at 4

link_tp_df['collision_at'] = link_tp_df['at']
link_tp_df.loc[ link_tp_df.collision_at < 4, 'collision_at' ]  = 4 # min cap at 4

link_tp_df = pandas.merge(how='left', left=link_tp_df, 
                          right=collisionlookup_df.rename(columns={'ft':'collision_ft','at':'collision_at'}), 
                          on=['collision_ft','collision_at'])
print("b link_tp_df len {}:\n{}".format(len(link_tp_df), link_tp_df.head()))
assert(len(link_tp_df) == len(periods)*num_links)

# for emission lookup
link_tp_df["speed"] = link_tp_df['cspd'].apply(numpy.int64)
link_tp_df.loc[ link_tp_df.speed > 65, "speed"] = 65 # cap at 65

# Transfer link x timeperiod attributes to link x timeperiod x vehicle class
link_tp_vehclass_df = pandas.merge(left=link_tp_vehclass_df, right=link_tp_df, how='left', on=id_fields+['timeperiod'])

# calculate VMT, VHT and Hypothetical FreeFlow Time
link_tp_vehclass_df['vmt'   ] = link_tp_vehclass_df['vol'] * link_tp_vehclass_df['distance']
link_tp_vehclass_df['vht'   ] = link_tp_vehclass_df['vol'] * link_tp_vehclass_df['ctim'] / 60.0
link_tp_vehclass_df['hypfft'] = link_tp_vehclass_df['vol'] * link_tp_vehclass_df['fft' ] / 60.0

# for this, we only care about ft=1 or ft=2 or ft==8 (freeway-to-freeway connectors, freeways, managed freeways)
# http://analytics.mtc.ca.gov/foswiki/Main/MasterNetworkLookupTables
link_tp_vehclass_df['nrcdelay'] = link_tp_vehclass_df['nrcdelay_pervmt']*link_tp_vehclass_df['vmt']
# so zero out non-freeway
link_tp_vehclass_df.loc[ ~link_tp_vehclass_df.ft.isin([1,2,8]), 'nrcdelay'] = 0.0
print("c link_tp_vehclass_df len {}:\n{}".format(len(link_tp_vehclass_df), link_tp_vehclass_df.head()))

# collisionlookup in collisions per 1000000 VMT
for collision_type in collision_types:
    link_tp_vehclass_df[collision_type] = link_tp_vehclass_df[collision_type]*link_tp_vehclass_df['vmt']

# join to vehicle class group and then emission lookup
vclassgroup_df = pandas.DataFrame.from_dict(vclassgroup, orient='index', columns=['vclassgroup'])
vclassgroup_df = vclassgroup_df.reset_index(drop=False).rename(columns={'index':'vclass'})
vclassgroup_df['vclass'] = vclassgroup_df['vclass'].str.lower()

link_tp_vehclass_df = pandas.merge(how='left', left=link_tp_vehclass_df, right=vclassgroup_df)
null_vclassgroup = link_tp_vehclass_df.loc[ pandas.isna(link_tp_vehclass_df.vclassgroup) ]
assert(len(null_vclassgroup) == 0)

if len(emissionslookup_df)>0:
    link_tp_vehclass_df = pandas.merge(how='left', left=link_tp_vehclass_df,
                                       right=emissionslookup_df.rename(columns={'period':'timeperiod'}))
    # verify merging with lookup didn't change the number of links/vclass/periods
    assert(len(link_tp_vehclass_df) == len(vclasses)*len(periods)*num_links)

    # emissionlookup in grams per mile (equivalent to metric tons per 1000000 VMT)
    for emission_type in emission_types:
        link_tp_vehclass_df[emission_type] = link_tp_vehclass_df[emission_type]*link_tp_vehclass_df['vmt']

print("d link_tp_vehclass_df len {}:\n{}".format(len(link_tp_vehclass_df), link_tp_vehclass_df.head()))

aggregate_dict = {'vmt'     :'sum',
                  'vht'     :'sum',
                  'hypfft'  :'sum',
                  'nrcdelay':'sum'}
for collision_type in collision_types: aggregate_dict[collision_type] = 'sum'
if len(emissionslookup_df)>0:
    for emission_type  in emission_types:  aggregate_dict[emission_type]  = 'sum'

# aggregate to timeperiod x vclass
metrics_df = link_tp_vehclass_df.groupby(['timeperiod','vclass']).aggregate(aggregate_dict).reset_index()

# create version with link mapping (e.g. link to TAZ)
link_tp_vehclass_mapped_df = pandas.DataFrame()
metrics_mapped_df          = pandas.DataFrame()
if args.link_mapping:
  link_tp_vehclass_mapped_df = link_tp_vehclass_df.merge(link_mapping_df, on=['a','b'], how='outer', indicator=True)
  print("Merged with link_mapping_df to create link_tp_vehclass_mapped_df with {} rows; head:\n{}".format(
        len(link_tp_vehclass_mapped_df), link_tp_vehclass_mapped_df.head(20)))

  # for aggregating, we'll want to multiply each variable by the share
  # so if a link is mapped to two indices, with 0.5 in one and 0.5 in the other
  # then the metrics will be split that way as well
  share_col = args.link_mapping[2]
  for metric_name in aggregate_dict.keys():
    print("  - multiplying {} by share col {}".format(metric_name, share_col))
    link_tp_vehclass_mapped_df[metric_name] = link_tp_vehclass_mapped_df[metric_name]*link_tp_vehclass_mapped_df[share_col]

  index_col = args.link_mapping[1]
  # set missing index_col value to -1
  link_tp_vehclass_mapped_df.fillna(value={index_col:-1}, inplace=True)

  # additional groupby columns
  # facility types: https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables#facility-type-ft
  link_tp_vehclass_mapped_df['road_type'] = 'non-freeway'
  link_tp_vehclass_mapped_df.loc[ link_tp_vehclass_mapped_df['ft'].isin([1,2,3,8]), 'road_type'] = 'freeway'
  # area types: https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables#area-type-at
  link_tp_vehclass_mapped_df['area_type'] = 'unset'
  # note DataFrame.at is a function so can't refer to it that way
  link_tp_vehclass_mapped_df.loc[ link_tp_vehclass_mapped_df['at'] <= 3, 'area_type'] = 'urban'
  link_tp_vehclass_mapped_df.loc[ link_tp_vehclass_mapped_df['at'] == 4, 'area_type'] = 'suburban'
  link_tp_vehclass_mapped_df.loc[ link_tp_vehclass_mapped_df['at'] == 5, 'area_type'] = 'rural'

  # and aggregate to timeperiod x vclass x road_type x area_type x indexcol
  metrics_mapped_df = link_tp_vehclass_mapped_df.groupby(['timeperiod','vclass','road_type','area_type',index_col]).aggregate(aggregate_dict).reset_index()
  print("  - aggregated to timeperiod, vclass, road_type, area_type, {}; head:\n{}".format(index_col, metrics_mapped_df.head(10)))

# collisionlookup in collisions per 1000000 VMT
for collision_type in collision_types: 
    metrics_df[collision_type] = metrics_df[collision_type]/1000000.0

    # ditto for mapped
    if len(metrics_mapped_df)>0: metrics_mapped_df[collision_type] = metrics_mapped_df[collision_type]/1000000.0

# emissionlookup in grams per mile (equivalent to metric tons per 1000000 VMT)
if len(emissionslookup_df)>0:
    for emission_type in emission_types:
        metrics_df[emission_type] = metrics_df[emission_type]/1000000.0

        # ditto for mapped
        if len(metrics_mapped_df)>0: metrics_mapped_df[emission_type] = metrics_mapped_df[emission_type]/1000000.0
  
# print(metrics_df.head())
metrics_df.rename(columns={'vclass':'vehicle class',
                           'vmt':'VMT',
                           'vht':'VHT',
                           'hypfft':'Hypothetical Freeflow Time',
                           'nrcdelay':'Non-Recurring Freeway Delay'},
                  inplace=True)
# ditto for mapped
if len(metrics_mapped_df) > 0:
  metrics_mapped_df.rename(columns={'vclass':'vehicle class',
                           'vmt':'VMT',
                           'vht':'VHT',
                           'hypfft':'Hypothetical Freeflow Time',
                           'nrcdelay':'Non-Recurring Freeway Delay'},
                  inplace=True)

output_cols = ["timeperiod","vehicle class","VMT","VHT","Hypothetical Freeflow Time", "Non-Recurring Freeway Delay"]+collision_types
if len(emissionslookup_df)>0:
  output_cols = output_cols + emission_types

metrics_df[output_cols].to_csv(vmt_vht_outputfile, header=True, index=False)
print("Wrote {}".format(vmt_vht_outputfile))

# write the mapped version aggregated to its index (e.g. TAZ)
if len(metrics_mapped_df) > 0:
  index_col     = args.link_mapping[1]
  output_suffix = args.link_mapping[3]
  vmt_vht_outputfile = vmt_vht_outputfile.replace(".csv","{}.csv".format(output_suffix))

  output_cols = [index_col, 'road_type', 'area_type'] + output_cols
  metrics_mapped_df[output_cols].to_csv(vmt_vht_outputfile, header=True, index=False)
  print("Wrote {}".format(vmt_vht_outputfile))

sys.exit(0)
