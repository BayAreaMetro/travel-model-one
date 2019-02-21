import csv, itertools, optparse, os, sys
import numpy, pandas

USAGE = """
 python hwynet.py hwynet.csv

 Reads the csv file of links from hwynet.csv and reports a number of
 metrics into metrics/vmt_vht_metrics by timeperiod and vehicle class.
 
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
"""
pandas.options.display.width = 1000
pandas.options.display.max_columns = 100

parser = optparse.OptionParser()
(options,args) = parser.parse_args()

datafile            = args[0]
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
print("Read {} links from {}".format(len(link_df), datafile))
id_fields    = ['a','b']
fields       = ['distance','lanes','at','ft','fft']

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
print("Melted to timeperiods: {} rows".format(len(link_tp_df)))
print(link_tp_df.head())

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
print("Melted to timeperiods x vehclasses: {} rows".format(len(link_tp_vehclass_df)))
print(link_tp_vehclass_df.head())

# units: Hours delay per VMT
# Map headers -> index for this lookup and read lookup data
nrc_file = os.path.join(lookupdir,"nonRecurringDelayLookup.csv")
nrclookup_df = pandas.read_csv(nrc_file, dtype={'vcratio':str}).set_index('vcratio')

# transform so columns are: vcratio (str), lanes_24(int), nrcdelay (float)
nrclookup_df.rename(columns={'2lanes':2, '3lanes':3, '4lanes':4}, inplace=True)
nrclookup_df = nrclookup_df.stack().reset_index().rename(columns={'level_1':'lanes_24',0:'nrcdelay'})
print("Read {}:\n{}".format(nrc_file, nrclookup_df.head()))

# Units are collisions per 1,000,000 VMT
# Map headers -> index for this lokup and read lookup data
collision_file = os.path.join(lookupdir,"collisionLookup.csv")
collisionlookup_df = pandas.read_csv(collision_file)
collision_types = list(collisionlookup_df.columns.values)
collision_types.remove('ft')
collision_types.remove('at')
collision_types.remove('lanes')
print("Read {}:\n{}".format(collision_file, collisionlookup_df.head()))

# Units are grams per mile (equivalent to metric tons per 1,000,000 VMT)
emission_file = os.path.join(lookupdir,"emissionsLookup.csv")
emissionslookup_df = pandas.read_csv(emission_file)
emission_types = list(emissionslookup_df.columns.values)
emission_types.remove('period')
emission_types.remove('vclassgroup')
emission_types.remove('speed')
print("Read {}:\n{}".format(emission_file, emissionslookup_df.head()))
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
# print("a link_tp_df:\n{}".format(link_tp_df.head()))

# for collision lookup
link_tp_df['collision_ft'] = link_tp_df['ft']
link_tp_df.loc[ link_tp_df.ft == 8,          'collision_ft'] =  2 # managed freeway is like a freeway
link_tp_df.loc[ link_tp_df.ft == 6,          'collision_ft'] = -1 # skip dummy links
link_tp_df.loc[ link_tp_df.lanes <= 0,       'collision_ft'] = -1 # or those with lanes <= 0
link_tp_df.loc[ link_tp_df.collision_ft > 4, 'collision_ft'] = 4 # cap at 4

link_tp_df['collision_lanes'] = link_tp_df['lanes']
link_tp_df.loc[ link_tp_df.collision_lanes > 4, 'collision_lanes'] = 4   # cap at 4

link_tp_df['collision_at'] = link_tp_df['at']
link_tp_df.loc[ link_tp_df.collision_at < 4, 'collision_at' ]  = 4 # min cap at 4

link_tp_df = pandas.merge(how='left', left=link_tp_df, 
                          right=collisionlookup_df.rename(columns={'ft':'collision_ft','at':'collision_at','lanes':'collision_lanes'}), 
                          on=['collision_ft','collision_lanes','collision_at'])
# print("b link_tp_df:\n{}".format(link_tp_df.head()))

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
# print("c link_tp_vehclass_df:\n{}".format(link_tp_vehclass_df.head()))

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

link_tp_vehclass_df = pandas.merge(how='left', left=link_tp_vehclass_df,
                                   right=emissionslookup_df.rename(columns={'period':'timeperiod'}))
# emissionlookup in grams per mile (equivalent to metric tons per 1000000 VMT)
for emission_type in emission_types:
    link_tp_vehclass_df[emission_type] = link_tp_vehclass_df[emission_type]*link_tp_vehclass_df['vmt']

#print("d link_tp_vehclass_df:\n{}".format(link_tp_vehclass_df.head()))
#print(len(link_tp_vehclass_df))

aggregate_dict = {'vmt'     :'sum',
                  'vht'     :'sum',
                  'hypfft'  :'sum',
                  'nrcdelay':'sum'}
for collision_type in collision_types: aggregate_dict[collision_type] = 'sum'
for emission_type  in emission_types:  aggregate_dict[emission_type]  = 'sum'

# aggregate to timeperiod x vclass
metrics_df = link_tp_vehclass_df.groupby(['timeperiod','vclass']).aggregate(aggregate_dict).reset_index()

# collisionlookup in collisions per 1000000 VMT
for collision_type in collision_types: 
    metrics_df[collision_type] = metrics_df[collision_type]/1000000.0

# emissionlookup in grams per mile (equivalent to metric tons per 1000000 VMT)
for emission_type in emission_types:
    metrics_df[emission_type] = metrics_df[emission_type]/1000000.0

# print(metrics_df.head())
metrics_df.rename(columns={'vclass':'vehicle class',
                           'vmt':'VMT',
                           'vht':'VHT',
                           'hypfft':'Hypothetical Freeflow Time',
                           'nrcdelay':'Non-Recurring Freeway Delay'},
                  inplace=True)

metrics_df[["timeperiod","vehicle class","VMT","VHT","Hypothetical Freeflow Time", "Non-Recurring Freeway Delay"]+
           collision_types+emission_types].to_csv(vmt_vht_outputfile, header=True, index=False)
print("Wrote {}".format(vmt_vht_outputfile))
sys.exit(0)
