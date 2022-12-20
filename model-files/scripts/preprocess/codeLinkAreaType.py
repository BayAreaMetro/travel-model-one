"""
Calculate TAZ Area Type Using Buffered Pop + Emp Density Measure
And Then Set Each Link Area Type to Nearest MAZ for Link A and B Node
python codeLinkAreaType.py model_directory

revised for BCM: jmh 07 2022
"""


import math, os, csv, sys
from rtree import index

model_run_dir = sys.argv[1]
TAZ_DATA_FILE = os.path.join(model_run_dir,r'landuse\taz_data_withdensity.csv')
NODE_CSV_FILE = os.path.join(model_run_dir,r'hwy\complete_network_with_tolls_nodes.csv')
LINK_CSV_FILE = os.path.join(model_run_dir,r'hwy\complete_network_with_tolls_links.csv')
AREA_TYPE_FILE = os.path.join(model_run_dir,r'hwy\link_area_type.csv')
BUFF_DIST       = 5280 * 0.5

print "Reading TAZ data"
tazData = []
with open(TAZ_DATA_FILE, 'rb') as csvfile:
  tazreader = csv.reader(csvfile, skipinitialspace=True)
  for row in tazreader:
    tazData.append(row)
tazDataColNames = tazData.pop(0)
print tazDataColNames
tazLandUse = dict()
origTazToSeqTaz = dict()
for row in tazData:
  taz = row[tazDataColNames.index("TAZ_ORIGINAL")]
  pop = row[tazDataColNames.index("TOTPOP")]
  emp = row[tazDataColNames.index("TOTEMPN")]
  acres = row[tazDataColNames.index("TOTACRE")]
  tazLandUse[taz] = [taz, pop, emp, acres,-1,-1,-1] #-1,-1,-1 = x,y,area type
  
  #create sequential lookup to join to network
  orig_taz_id = row[tazDataColNames.index("TAZ_ORIGINAL")]
  origTazToSeqTaz[orig_taz_id] = taz

print "Reading nodes"
tazs = dict()
nodes = dict()
spIndexTaz = index.Index()
with open(NODE_CSV_FILE,'rb') as node_file:
  node_reader = csv.reader(node_file,skipinitialspace=True)
  for row in node_reader:
    n = row[0]
    xCoord = float(row[1])
    yCoord = float(row[2])
    if n in origTazToSeqTaz:
      tazLandUse[origTazToSeqTaz[n]][4] = xCoord
      tazLandUse[origTazToSeqTaz[n]][5] = yCoord
      spIndexTaz.insert(int(origTazToSeqTaz[n]), (xCoord, yCoord, xCoord, yCoord))
    nodes[n] = [n, xCoord, yCoord]

print "Calculate buffered MAZ measures"
print tazLandUse.keys()
for k in tazLandUse.keys():
  
  #get maz data
  x = float(tazLandUse[k][4])
  y = float(tazLandUse[k][5])
  
  total_pop = 0
  total_emp = 0
  total_acres = 0

  #get all mazs within square box around maz
  idsList = spIndexTaz.intersection((x-BUFF_DIST, y-BUFF_DIST, x+BUFF_DIST, y+BUFF_DIST))
  
  for id in idsList:
    
    pop = int(float(tazLandUse[str(id)][1]))
    emp = int(float(tazLandUse[str(id)][2]))
    acres = float(tazLandUse[str(id)][3])
    
    #accumulate measures
    total_pop = total_pop + pop
    total_emp = total_emp + emp
    total_acres = total_acres + acres
  
  #calculate buffer area type
  if total_acres>0:
    tazLandUse[k][6] = (1 * total_pop + 2.5 * total_emp) / total_acres
  else:
    tazLandUse[k][6] = 0
  
  #code area type class
  if tazLandUse[k][6] < 6:
    tazLandUse[k][6] = 5 #rural
  elif tazLandUse[k][6] < 30:
    tazLandUse[k][6] = 4 #suburban
  elif tazLandUse[k][6] < 55:
    tazLandUse[k][6] = 3 #urban
  elif tazLandUse[k][6] < 100:
    tazLandUse[k][6] = 2 #urban business
  elif tazLandUse[k][6] < 300:
    tazLandUse[k][6] = 1 #cbd
  else:
    tazLandUse[k][6] = 0 #regional core

print "Find nearest MAZ for each link, take min area type of A or B node"
lines = ["A,B,AREATYPE" + os.linesep]

with open(LINK_CSV_FILE,'rb') as link_file:
  link_reader = csv.reader(link_file,skipinitialspace=True)
  for row in link_reader:
    a = int(row[0])
    b = int(row[1])
    cntype = row[2]
    ax = nodes[str(a)][1]
    ay = nodes[str(a)][2]
    bx = nodes[str(b)][1]
    by = nodes[str(b)][2]
    
    #find nearest, take min area type of A or B node
    if cntype in ["TANA","USE","TAZ","EXT"]:
      aTaz = list(spIndexTaz.nearest((ax, ay, ax, ay), 1))[0]
      bTaz = list(spIndexTaz.nearest((bx, by, bx, by), 1))[0]
      aAT = tazLandUse[str(aTaz)][6]
      bAT = tazLandUse[str(bTaz)][6]
      linkAT = min(aAT, bAT)
    else:
      linkAT = -1 #NA
      
    #add to output file
    lines.append("%i,%i,%i%s" % (a, b, linkAT, os.linesep))

#create output file
print "Write link area type CSV file"
outFile = open(AREA_TYPE_FILE, "wb")
outFile.writelines(lines)
outFile.close()
