import csv, optparse, os
from xlrd import *

USAGE = """
 python transit.py quickboards.xls

 Opens the given quickboards workbook and tallies Daily Boardings and Daily Passenger Miles for each
 mode type (local, express, ferry, lrt, heavy rail, commuter rail, advanced air mobility).  
 Mode type is interpretted based on the line name numeric prefix.

 Outputs result into metrics\transit_boards_miles.csv
 RSG 2022-01-21 TM1.5 add advanced air mobility mode
 """

parser = optparse.OptionParser()
(options,args) = parser.parse_args()

datafile 	= args[0]
outputfile 	= os.path.join("metrics","transit_boards_miles.csv")

print('summarizing transit boardings and passenger miles')

# read data, prepare to write
wkbk = open_workbook(datafile,encoding_override="cp1252")
sheet = wkbk.sheet_by_index(0)

boardings = {}
passmiles = {}

rownum = 3
while True:
	try:
		line = sheet.cell_value(rownum,0)
	except IndexError:
		#done
		break

	# done
	if line == '':
		break

	split_idx = line.find('_')
	mode = int(line[0:split_idx])
	if mode < 80:
		mode_str = 'loc'
	elif mode < 100:
		mode_str = 'exp'
	elif mode < 110:
		mode_str = 'lrf'
	elif mode < 120:
		mode_str = 'lrf'
	elif mode < 130:
		mode_str = 'hvy'
	elif mode < 140:
		mode_str = 'com'		
	else:
		mode_str = 'aam'

	if mode_str not in boardings: boardings[mode_str] = 0.0
	if mode_str not in passmiles: passmiles[mode_str] = 0.0

	daily_boards = sheet.cell_value(rownum,1)
	if daily_boards != '': boardings[mode_str] += daily_boards

	daily_pmt = sheet.cell_value(rownum,15)
	if daily_pmt != '':	passmiles[mode_str] += daily_pmt
	
	rownum+=1

print boardings

outfile = open(outputfile, 'w')
writer = csv.writer(outfile,lineterminator='\n')
writer.writerow(['Transit mode','Daily Boardings','Daily Passenger Miles Traveled'])
for mode_str in ['loc','exp','lrf','hvy','com','aam']:
	writer.writerow([mode_str,boardings[mode_str],passmiles[mode_str]])
outfile.close()