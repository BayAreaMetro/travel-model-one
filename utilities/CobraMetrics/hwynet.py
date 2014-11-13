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
  * Motor Vehicle Fatality:
  * Motor Vehicle Injury:
  * Motor Vehicle Property:
  * Walk Fatality:
  * Walk Injury:
  * Bike Fatality:
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
"""
parser = optparse.OptionParser()
(options,args) = parser.parse_args()

datafile            = args[0]
lookupdir           = os.path.join( "INPUT","metrics" )
vmt_vht_outputfile  = os.path.join("metrics", "vmt_vht_metrics.csv")
vclasses            = ['DA','S2','S3','SM','HV','DAT','S2T','S3T','SMT','HVT']
vclassgroup         = {'DA':'auto',  'DAT':'auto', # use for emissions
                       'S2':'auto',  'S2T':'auto',
                       'S3':'auto',  'S3T':'auto',
                       'SM':'SM',    'SMT':'SM',
                       'HV':'HV',    'HVT':'HV'}
periods             = ['EA','AM','MD','PM','EV']

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

# TODO: What are the units in this file?  Hours delay per VMT?  Minutes?
# Map headers -> index for this lookup and read lookup data
nrclookup       = {} # key = vcratio, as string, %.2f
infile    		= open(os.path.join(lookupdir,"nonRecurringDelayLookup.csv"))
reader    		= csv.reader(infile)
nrc_header_list = reader.next()
nrc_headers     = {nrc_header_list[i]:i for i in range(len(nrc_header_list))}
for row in reader:
	nrclookup[row[nrc_headers['vcratio']]] = row
infile.close()
# print nrclookup

# TODO: Units are collisions per 1,000,000 VMT?
# Map headers -> index for this lokup and read lookup data
collisionlookup = {} # key = (at,ft,lanes)
infile        	= open(os.path.join(lookupdir,"collisionlookup.csv"))
reader          = csv.reader(infile)
col_header_list = reader.next()
col_headers     = {col_header_list[i]:i for i in range(len(col_header_list))}
for row in reader:
	collisionlookup[( int(row[col_headers['at']]),
		              int(row[col_headers['ft']]),
		              int(row[col_headers['lanes']]) )] = row
collision_types = col_header_list[3:]
infile.close()
# print collisionlookup

# TODO: Units are Metric Tons per 1,000,000 VMT?
emissionslookup = {} # key = (period,vclassgroup,speed)
infile        	= open(os.path.join(lookupdir,"emissionsLookup.csv"))
reader          = csv.reader(infile)
em_header_list  = reader.next()
em_headers      = {em_header_list[i]:i for i in range(len(em_header_list))}
for row in reader:
	emissionslookup[( row[em_headers['period']],
		              row[em_headers['vclassgroup']],
		              int(row[em_headers['speed']]) )] = row
emission_types = em_header_list[3:]
infile.close()

print('Calculating vmt and vht by vehicle class and period...')
# Sum up VMT, VHT and Hypothetical Free Flow Time by period and vehicle class
vht 	= {} # Key = (period,vclass)  e.g. ('AM','DA')
vmt 	= {} # Key = (period,vclass)  e.g. ('AM','DA')
hypfft  = {} # Key = (period,vclass)  e.g. ('AM','DA')

vmt_vcl = {} # Key = (period,vclass,vcratio str,lanes (2,3,4))
             # Note: This is only for ft=1 or ft=2 (freeway-to-freeway connectors, freeways)

vmt_collisions = {} # Key = (period,vclass,at,ft,lanes)
                    # at is 4 (non-rural) or 5(rural)
                    # ft is 1-4 (6 not included, 5+ called 4)
                    # lanes is 1-4 (5+ called 4)
vmt_emissions  = {} # Key = (period,vclass,speed) where speed is capped at 65

# Initialize tally dictionaries
for period in periods:
	for vclass in vclasses:
		vht[(period,vclass)] 	= 0.0
		vmt[(period,vclass)] 	= 0.0
		hypfft[(period,vclass)]	= 0.0

		for vcratio in range(101):
			for lanes in [2,3,4]:
				vmt_vcl[(period,vclass,"%.2f" % (vcratio*0.01),lanes)] = 0.0
		
		for at in [4,5]:
			for ft in [1,2,3,4]:
				for lanes in [1,2,3,4]:
					vmt_collisions[(period,vclass,at,ft,lanes)] = 0.0

		for speed in range(66):
			vmt_emissions[(period,vclass,speed)] = 0.0


# Tally VMT, VHT, Hypothetical Freeflow Time
for ab,row in data.iteritems():
	for period in periods:
		for vclass in vclasses:
			volname = 'vol' + period + '_' + vclass.lower()
			timname = 'ctim' + period

			_vmt = float( row[headers[volname]] ) * float( row[headers['distance']] )

			vmt[(period,vclass)]    += _vmt
			vht[(period,vclass)]    += float( row[headers[volname]] ) * \
			                           float( row[headers[timname]] ) / 60.0
			
			hypfft[(period,vclass)] += float( row[headers[volname]] ) * \
			                           float( row[headers['fft']]   ) / 60.0

			# for this, we only care about ft=1 or ft=2 (freeway-to-freeway connectors, freeways)
			# http://analytics.mtc.ca.gov/foswiki/Main/MasterNetworkLookupTables
			if int( row[headers['ft']] ) <= 3:
				vcratio = "%.2f" % min(1.0, float(row[headers['vc'+period]]))
				lanes   = int(row[headers['lanes']])
				if lanes < 2: lanes = 2
				if lanes > 4: lanes = 4
				vmt_vcl[(period,vclass,vcratio,lanes)] += _vmt

			# skip Dummy links
			if int( row[headers['ft']]) != 6:
				ft = min( int( row[headers['ft']] ), 4) 		# cap at 4
				at = max( int( row[headers['at']] ), 4) 		# min cap at 4
				lanes = min( int( row[headers['lanes']]), 4) 	# cap at 4
				vmt_collisions[(period,vclass,at,ft,lanes)] += _vmt

			cspd = float(row[headers['cspd'+period]])
			cspd = min( int(cspd), 65) # cap at 65
			vmt_emissions[(period,vclass,cspd)] += _vmt

# Write out results
outfile = open(vmt_vht_outputfile, 'w')
writer  = csv.writer(outfile,lineterminator='\n')			
writer.writerow(['timeperiod', 'vehicle class', 
	'VMT', 
	'VHT',
	'Hypothetical Freeflow Time',
	'Non-Recurring Freeway Delay'] + collision_types + emission_types)
for period in periods:
	for vclass in vclasses:

		# Sum the non-recurring freeway delay for this period/vclass
		nrcdelay = 0.0
		for vcratio in range(101):
			vcratio_str = "%.2f" % (vcratio*0.01)
			for lanes in [2,3,4]:
				nrcdelay += vmt_vcl[(period,vclass,vcratio_str,lanes)] * \
				            float(nrclookup[vcratio_str][nrc_headers['%dlanes' % lanes]])

		# Sum the estimated collisions
		collision_tallies = [0.0]*len(collision_types)
		for at in [4,5]:
			for ft in [1,2,3,4]:
				for lanes in [1,2,3,4]:
					for idx in range(len(collision_types)):
						collision_tallies[idx] += vmt_collisions[(period,vclass,at,ft,lanes)] * \
		   					                      float(collisionlookup[(at,ft,lanes)][col_headers[collision_types[idx]]])
		# collisionlookup in collisions per 1000000 VMT
		for idx in range(len(collision_tallies)):
			collision_tallies[idx] = collision_tallies[idx]/1000000.0

		# Sum the estimated emissions
		emission_tallies = [0.0]*len(emission_types)
		for speed in range(66):
			for idx in range(len(emission_types)):
				emission_tallies[idx] += vmt_emissions[(period,vclass,speed)] *\
				                         float(emissionslookup[(period,vclassgroup[vclass],speed)][em_headers[emission_types[idx]]])
		# emissionlookup in emissions per 1000000 VMT
		for idx in range(len(emission_tallies)):
			emission_tallies[idx] = emission_tallies[idx]/1000000.0

		writer.writerow([period, vclass, 
			vmt[(period,vclass)],
			vht[(period,vclass)],
			hypfft[(period,vclass)],
			nrcdelay] + collision_tallies + emission_tallies)
outfile.close()
print("Wrote %s" % vmt_vht_outputfile)
