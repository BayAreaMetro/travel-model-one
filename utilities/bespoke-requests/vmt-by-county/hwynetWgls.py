import csv, optparse, os, sys

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
parser = optparse.OptionParser()
(options,args) = parser.parse_args()

datafile            = args[0]
lookupdir           = os.path.join( "INPUT","metrics" )
vmt_vht_outputfile  = os.path.join("metrics", "vmt_vht_metrics_by_county_2040_06_694_NewBase_MareIsland_Final..csv")
vclasses            = ['DA','S2','S3','SM','HV','DAT','S2T','S3T','SMT','HVT']
vclassgroup         = {'DA':'auto',  'DAT':'auto', # use for emissions
                       'S2':'auto',  'S2T':'auto',
                       'S3':'auto',  'S3T':'auto',
                       'SM':'SM',    'SMT':'SM',
                       'HV':'HV',    'HVT':'HV'}
periods             = ['EA','AM','MD','PM','EV']
#gls                 = ['1','2','3','4','5','6','7','8','9']
gls                 = [1,2,3,4,5,6,7,8,9,10]
#gls                 = ['San Francisco','San Mateo','Santa Clara','Alameda',
#                       'Contra Costa','Solano','Napa','Sonoma','Marin']

# Store the link data
infile 			= open(datafile)
data    		= {}
reader 			= csv.reader(infile)
header_list 	= reader.next()
headers     	= {header_list[i]:i for i in range(len(header_list))}
for row in reader:
	data[( int(row[headers['a']]),
		   int(row[headers['b']]) )] = row
infile.close()
# print headers

# units: Hours delay per VMT
# Map headers -> index for this lookup and read lookup data
nrclookup       = {} # key = vcratio, as string, %.2f
infile    		= open("nonRecurringDelayLookup.csv")
reader    		= csv.reader(infile)
nrc_header_list = reader.next()
nrc_headers     = {nrc_header_list[i]:i for i in range(len(nrc_header_list))}
for row in reader:
	nrclookup[row[nrc_headers['vcratio']]] = row
infile.close()
# print nrclookup

print('Calculating vmt and vht by vehicle class and period...')
# Sum up VMT, VHT and Hypothetical Free Flow Time by county, period and vehicle class
vht 	= {} # Key = (gl,period,vclass)  e.g. ('AM','DA')
vmt 	= {} # Key = (gl,period,vclass)  e.g. ('AM','DA')
hypfft  = {} # Key = (gl,period,vclass)  e.g. ('AM','DA')

vmt_vcl = {} # Key = (gl,period,vclass,vcratio str,lanes (2,3,4))
             # Note: This is only for ft=1 or ft=2 (freeway-to-freeway connectors, freeways)

# Initialize tally dictionaries
for gl in gls:
  for period in periods:
	for vclass in vclasses:
		vht[(gl,period,vclass)] 	= 0.0
		vmt[(gl,period,vclass)] 	= 0.0
		hypfft[(gl,period,vclass)]	= 0.0

		for vcratio in range(101):
			for lanes in [2,3,4]:
				vmt_vcl[(gl,period,vclass,"%.2f" % (vcratio*0.01),lanes)] = 0.0
		

# Tally VMT, VHT, Hypothetical Freeflow Time
for ab,row in data.iteritems():
   # for gl in gls:
	  for period in periods:
		for vclass in vclasses:
			volname = 'vol' + period + '_' + vclass.lower()
			timname = 'ctim' + period

			_vmt = float( row[headers[volname]] ) * float( row[headers['distance']] )

			vmt[(int( row[headers['gl']] ),period,vclass)]    += _vmt
			vht[(int( row[headers['gl']] ),period,vclass)]    += float( row[headers[volname]] ) * \
			                           float( row[headers[timname]] ) / 60.0
			
			hypfft[(int( row[headers['gl']] ),period,vclass)] += float( row[headers[volname]] ) * \
			                           float( row[headers['fft']]   ) / 60.0

			# for this, we only care about ft=1 or ft=2 or ft==8 (freeway-to-freeway connectors, freeways, managed freeways)
			# http://analytics.mtc.ca.gov/foswiki/Main/MasterNetworkLookupTables
			if int( row[headers['ft']] ) in [1,2,8]:
				vcratio = "%.2f" % min(1.0, float(row[headers['vc'+period]]))
				lanes   = int(row[headers['lanes']])
				if lanes < 2: lanes = 2
				if lanes > 4: lanes = 4
				vmt_vcl[(int( row[headers['gl']] ),period,vclass,vcratio,lanes)] += _vmt

# Write out results
outfile = open(vmt_vht_outputfile, 'w')
writer  = csv.writer(outfile,lineterminator='\n')			
writer.writerow(['gl','timeperiod', 'vehicle class', 
	'VMT', 
	'VHT',
	'Hypothetical Freeflow Time',
	'Non-Recurring Freeway Delay'])
for gl in gls:
  for period in periods:
	for vclass in vclasses:

		# Sum the non-recurring freeway delay for this period/vclass
		nrcdelay = 0.0
		for vcratio in range(101):
			vcratio_str = "%.2f" % (vcratio*0.01)
			for lanes in [2,3,4]:
				nrcdelay += vmt_vcl[(gl,period,vclass,vcratio_str,lanes)] * \
				            float(nrclookup[vcratio_str][nrc_headers['%dlanes' % lanes]])
		writer.writerow([gl,period, vclass, 
			vmt[(gl,period,vclass)],
			vht[(gl,period,vclass)],
			hypfft[(gl,period,vclass)],
			nrcdelay])
outfile.close()
print("Wrote %s" % vmt_vht_outputfile)
