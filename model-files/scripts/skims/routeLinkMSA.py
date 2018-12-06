''' See USAGE
'''
import csv, logging, os, sys

# we only want to use this specific version of wrangler
libdir = os.path.realpath(os.path.join(os.path.split(__file__)[0], "..", "..", "lib"))
sys.path.insert(0,libdir)

from Wrangler import setupLogging, Network, TransitAssignmentData, TransitNetwork

USAGE = """

python routeLinkMSA AM|MD|PM|EV|EA trnAssignIter VolumeDiffCondition

 For trnAssignIter=1, just aggregates the assignment files across submodes into trnlink[timeperiod]_ALLMSA.dbf
 
 For trnAssignIter>1,
   1. Read in previous iteration's aggregated assignment dbf (MSA'd)
   2. Read in current iteration's raw volumes
   3. Checks if the volumes have changed little (e.g. total change over total vol < VolumeDiffCondition)
   4.   If they're unchanged, then we're converged; do nothing
   5.   Otherwise, continue; MSA this iteration's volumes and output new trnlink[timeperiod]_ALLMSA.dbf

 Keeps running log in RouteLinkMSALog.csv
 
"""


if len(sys.argv) != 4:
    print USAGE
    exit(1)
    
timeperiod              = sys.argv[1]
trnAssignIter           = int(sys.argv[2])
volDiffCond             = float(sys.argv[3])

subdir                  = "Subdir"+str(trnAssignIter)
routeFileName           = os.path.join(subdir, "trnlink{}_ALLMSA.dbf".format(timeperiod))

setupLogging(infoLogFilename=None, debugLogFilename="routeLinkMSA_%s.%d.log" % (timeperiod, trnAssignIter), 
             logToConsole=False)
    

# Read in the current assignment
logging.info("Reading in transit assignment data for " + timeperiod)
TransitNetwork.initializeTransitCapacity(directory="..")
curTad=TransitAssignmentData(timeperiod=timeperiod,
                             modelType=Network.MODEL_TYPE_TM1,
                             ignoreModes=[1,2,3,4,5,6,7],
                             tpfactor="constant_with_peaked_muni",
                             transitCapacity=TransitNetwork.capacity)

if trnAssignIter == 0:
    prevTad = False
else:
    prevSubdir              = "Subdir"+str(trnAssignIter-1)
    prevRouteFileName       = os.path.join(prevSubdir, "trnlink{}_ALLMSA.dbf".format(timeperiod))    
    # Read the MSA assignment from the previous iteration
    prevTad=TransitAssignmentData(timeperiod=timeperiod,
                                  modelType=Network.MODEL_TYPE_TM1,
                                  ignoreModes=[1,2,3,4,5,6,7],
                                  tpfactor="constant_with_peaked_muni",
                                  transitCapacity=TransitNetwork.capacity,                                  
                                  lineLevelAggregateFilename=prevRouteFileName)

LAMBDA       = float(1.0/float(trnAssignIter+1))
totVol       = 0
totalDeltaVol= 0

for row in curTad.trnAsgnTable:
    key      = row["ABNAMESEQ"]
    totVol  += row["AB_VOL"]
    
    # MSA function for curVol
    if prevTad:
        try:
            row["AB_VOL"]  = (LAMBDA*row["AB_VOL"]) +((1.0-LAMBDA)*prevTad.trnAsgnTable[key]["AB_VOL" ])
            row["AB_BRDA"] = (LAMBDA*row["AB_BRDA"])+((1.0-LAMBDA)*prevTad.trnAsgnTable[key]["AB_BRDA"])
            row["AB_XITA"] = (LAMBDA*row["AB_XITA"])+((1.0-LAMBDA)*prevTad.trnAsgnTable[key]["AB_XITA"])
            row["AB_BRDB"] = (LAMBDA*row["AB_BRDB"])+((1.0-LAMBDA)*prevTad.trnAsgnTable[key]["AB_BRDB"])
            row["AB_XITB"] = (LAMBDA*row["AB_XITB"])+((1.0-LAMBDA)*prevTad.trnAsgnTable[key]["AB_XITB"])
        
            row["BA_VOL"]  = (LAMBDA*row["BA_VOL"]) +((1.0-LAMBDA)*prevTad.trnAsgnTable[key]["BA_VOL" ])
            row["BA_BRDA"] = (LAMBDA*row["BA_BRDA"])+((1.0-LAMBDA)*prevTad.trnAsgnTable[key]["BA_BRDA"])
            row["BA_XITA"] = (LAMBDA*row["BA_XITA"])+((1.0-LAMBDA)*prevTad.trnAsgnTable[key]["BA_XITA"])
            row["BA_BRDB"] = (LAMBDA*row["BA_BRDB"])+((1.0-LAMBDA)*prevTad.trnAsgnTable[key]["BA_BRDB"])
            row["BA_XITB"] = (LAMBDA*row["BA_XITB"])+((1.0-LAMBDA)*prevTad.trnAsgnTable[key]["BA_XITB"])
        
            deltaVol = abs(row["AB_VOL"]-prevTad.trnAsgnTable[key]["AB_VOL"])
        
            #Add absolute diff and total up for convergence calc to follow
            totalDeltaVol   += deltaVol
        except:
            print "An error occurred in MSAing for link [%s]" % key
            print sys.exc_info()
            print "Skipping..."
            
# Convergence criteria: is the change in volume (as a fraction of the total volumes) small enough?
# When we have met the convergence criteria, we do not create a new "trnlink[timeperiod]_ALLMSA.dbf"
criteriaMet = False
pctDiffVol = totalDeltaVol/totVol
if prevTad and pctDiffVol < volDiffCond:
    criteriaMet = True

# Might two different try do do this at the same time?
f = open("RouteLinkMSALog.csv","a")
f.write("%d,%s,%f,%f,%d\n" % (trnAssignIter,timeperiod,totVol,pctDiffVol,criteriaMet))
f.close()

# write the link sum aggregates if it's the last one
linkSumFileName = None
if criteriaMet:
    linkSumFileName=routeFileName.replace(".dbf", "_linksum.dbf")
    
# Write out the assignment
curTad.writeDbfs(asgnFileName=routeFileName, aggregateFileName=linkSumFileName)