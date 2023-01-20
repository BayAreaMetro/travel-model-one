'''Modify Transit Dwell Time and Access

Created on Aug 12, 2010

'''
import csv, glob, os, re, sys, traceback
from math import pow, sqrt
from collections import defaultdict

from Wrangler import setupLogging, Network, TransitLine, TransitNetwork, TransitAssignmentData, WranglerLogger
from dataTable import DataTable, FieldType

USAGE = """
python transitDwellAccess.py [POSTPROC|NORMAL] [extraDelayFile|NoExtraDelay] [Simple]|[Complex AM|MD|PM|EV|EA trnAssignIter phtdiffcond maxiters]
  complexDwell dmode1 dmode2 .. dmodeN complexAccess amode1 amode2 ... amode3

  For Simple mode, this just demuxes the transitLines into the timeperiod-specific versions, and
    assigns simple dwell delays based on the mode, outputs transitOriginal[timeperiods].lin
    Additionally outputs transitVehicleVolsOnLink[timeperiod].dbf for assignment to the roadway network,
    with A,B,AB,TRNVEHVOL attributes.
  An optional *extraDelayFile* can be passed in for Simple mode, a .csv file with columns:
    Line_names (space-delimited), stop number, delay_am, delay_md, delay_pm, delay_ev, delay_ea.
    The delays are floats and are minutes.

  For Complex mode, the
  - trnAssignIter is the transit assignment iteration
  - phtdiffcond is the conditional (relative gap) for PHT; pass 0 if no check 
    (in which case, msa volume are used instead)
  - maxiters is the maximum number of transit assignment iterations we'll go to
  - dmode1 dmode2 ... are the transit modes for complex delay.  May be "None".
  - amode1 amode2 ... are the transit modes for access modifications.  May be "None"
"""

def updateLinesOfInterest(timeperiod, trnAssignIter, complexAccessModes, currentTad, currentNet):
    """ 
    Reads and updates a linesOfInterest[timeperiod].csv file to include
    volumes and if boardings are disallowed for easy graphing.
    """
    LOIfile         = "linesOfInterest" + timeperiod + ".csv"
    lineStopToRowIdx= {}  # linename + stopnode -> rowIdx
    newFile         = False
    
    # initialize with file contents
    if os.path.exists(LOIfile):
        linesOfInterest = []
        reader = csv.reader(open(LOIfile, "rb"))
        for row in reader:
            linesOfInterest.append(row)
            if len(row)>0: lineStopToRowIdx[row[0] + row[1]] = len(linesOfInterest)-1
    else:
        # initialize with header
        newFile = True
        linesOfInterest = [["linename", "stopnode", "stopdesc"]]
        lineStopToRowIdx["linename"] = 0
        
    # add one or two columns
    if len(linesOfInterest[0]) == 3:
        volIdx = 3
    else:
        numCols = (len(linesOfInterest[0])-3)/2
        volIdx = len(linesOfInterest[0])-numCols
        
    
    # update header
    linesOfInterest[0].insert(volIdx,"vol%d" % (trnAssignIter))
    linesOfInterest[0].append("noboard%d" % (trnAssignIter))
    
    # update cols -- everything in COMPLEXMODES_ACCESS
    comp_modes_strs = list("{}".format(x) for x in complexAccessModes)
    comp_modes_str  = str("|").join(comp_modes_strs)
    comp_modes_re   = "^({})_".format(comp_modes_str)
    for line in currentNet.line(re.compile(comp_modes_re)):
        
        if line.getFreq(timeperiod,Network.MODEL_TYPE_TM1)==0.0: continue
        
        for nodeIdx in range(len(line.n)-1):
            node = line.n[nodeIdx]
            if not node.isStop(): continue
            
            try:
                vol = currentTad.linkVolume(line.name, 
                                            abs(int(node.num)), abs(int(line.n[nodeIdx+1].num)), 
                                            nodeIdx+1)
            except:
                print sys.exc_info()

            boardsDisallowed = int(node.boardsDisallowed())
            
            if newFile:
                linesOfInterest.append([line.name, node.num, node.description(),
                                        vol, boardsDisallowed])
            elif line.name:
                rowIdx = lineStopToRowIdx[line.name + str(node.num)]
                linesOfInterest[rowIdx].insert(volIdx, vol)
                linesOfInterest[rowIdx].append(boardsDisallowed)
        
    writer = csv.writer(open(LOIfile, "wb"))
    writer.writerows(linesOfInterest)

def updatePHT(timeperiod, trnAssignIter, maxTrnAssignIter, PHTDiffCond):
    """
    Read PHT history and add this iteration's results into a consolidated log, PHT_Total.csv.
    Returns criteriaMet boolean.
    """
    criteriaMet= False
    allPHTFile = open("PHT_total.csv", "a")
    PHT        = {} # iteration => timeperiod => PHT
    Modes      = {}
    phtFiles   = glob.glob('PHT_total_*.csv')
    # assert(len(phtFiles)==45)
    
    # for this trnAssignIter, for this timeperiod
    boards     = 0
    avgpaths   = 0
    currpaths  = 0 
    ivttSE     = 0.0
    tottSE     = 0.0
    pathFromBoth = 0
    pathFromIter = 0
    pathFromAvg  = 0
    
    for phtFile in phtFiles:
        # print("Reading phtFile {}".format(phtFile))
        logReader=csv.reader(open(phtFile))
        for phtIterationStr,phtTimeperiod,Mode,PHTStr,RMSEivttStr,RMSEtottStr,AvgPathsStr,CurrPathsStr,CurrBoardsStr, \
                PathFromBothStr,PathFromIterOnlyStr,PathFromAvgOnlyStr in logReader:
            phtTimeperiod = phtTimeperiod.upper() # normalize
            phtIteration    = int(phtIterationStr)
            PHTval          = float(PHTStr)
            CurrBoardsval   = float(CurrBoardsStr)
            
            if phtIteration not in PHT:
                PHT[phtIteration]    = {}
                Modes[phtIteration]  = {}
            if phtTimeperiod not in PHT[phtIteration]:
                PHT[phtIteration][phtTimeperiod] = 0
                Modes[phtIteration][phtTimeperiod] = []
                
            # if the line is a dupe, ignore (this can happen if processes are restarted)
            if Mode in Modes[phtIteration][phtTimeperiod]: continue
            Modes[phtIteration][phtTimeperiod].append(Mode)
    
            PHT[phtIteration][phtTimeperiod] += PHTval
            
            # only append to the total file for the relevant timeperiod and iteration
            # otherwise it'll be full of dupes
            #   trnAssignIter,timeperiod,mode,PHT,pctPHTdiff,
            #   RMSE_IVTT,RMSE_TOTT,AvgPaths,CurrPaths,Boards,PHTCriteriaMet > PHT_total.csv

            if phtTimeperiod==timeperiod and phtIteration==trnAssignIter:
                boards    += CurrBoardsval
                avgpaths  += int(AvgPathsStr) 
                currpaths += int(CurrPathsStr)
                ivttSE    += float(RMSEivttStr)*float(RMSEivttStr)*float(CurrPathsStr)
                tottSE    += float(RMSEtottStr)*float(RMSEtottStr)*float(CurrPathsStr)
                pathFromBoth += int(PathFromBothStr)
                pathFromIter += int(PathFromIterOnlyStr)
                pathFromAvg  += int(PathFromAvgOnlyStr)
                
                allPHTFile.write("%d,%s,%s,%f,,%s,%s,%s,%s,%f,%s,%s,%s,\n" % 
                                 (phtIteration,phtTimeperiod,Mode,PHTval,#pctPHTdiff
                                  RMSEivttStr,RMSEtottStr,AvgPathsStr,CurrPathsStr,
                                  CurrBoardsval, PathFromBothStr,PathFromIterOnlyStr,PathFromAvgOnlyStr #,PhTCriteriaMet
                                  ))
        
    # First iteration -- nothing to do
    if currpaths == 0:
        print "Currpaths = 0 for {},{},{}".format(phtIterationStr,phtTimeperiod,Mode)
        RMSEivtt = 0
        RMSEtott = 0
    else:
        RMSEivtt = sqrt(ivttSE/float(currpaths))
        RMSEtott = sqrt(tottSE/float(currpaths))
    if trnAssignIter == 0:
        allPHTFile.write("%d,%s,%s,%f,,%f,%f,%d,%d,%f,%d,%d,%d,\n" % (trnAssignIter,timeperiod,"Total",
                                                             PHT[trnAssignIter][timeperiod], #pctPHTdiff
                                                             RMSEivtt, RMSEtott, 
                                                             avgpaths, currpaths, boards,
                                                             pathFromBoth, pathFromIter, pathFromAvg))
        # in case we're only running this one
        if trnAssignIter==maxTrnAssignIter: criteriaMet = True

    # otherwise -- Check convergence
    else:
        # print PHT
        currPHT = PHT[trnAssignIter][timeperiod]
        prevPHT = PHT[trnAssignIter-1][timeperiod]
        pctdiffPHT = (currPHT-prevPHT)/prevPHT
    
        if trnAssignIter==maxTrnAssignIter or (PHTDiffCond > 0 and abs(pctdiffPHT) <= PHTDiffCond):
            criteriaMet = True
            
        # Put the total in the PHT_total.csv as well
        allPHTFile.write("%d,%s,%s,%f,%f,%f,%f,%d,%d,%f,%d,%d,%d,%d\n" % (trnAssignIter,timeperiod,"Total",
                                                                 currPHT,pctdiffPHT, 
                                                                 RMSEivtt, RMSEtott, 
                                                                 avgpaths, currpaths, boards, 
                                                                 pathFromBoth, pathFromIter, pathFromAvg,
                                                                 criteriaMet))
    allPHTFile.close()
    return criteriaMet

def checkMSAcriteriaMet(timeperiod, trnAssignIter):
    """
    Check the RouteLinksMSALog.csv to see if we've converged.
    Returns criteriaMet boolean.    
    """
    routelinkFile = open("RouteLinkMSALog.csv", "rb")
    logReader=csv.reader(routelinkFile)
    for trnAssignIterStr, timeperiodStr, totVolStr, pctDiffVolStr, criteriaMetStr in logReader:
        if timeperiodStr == timeperiod and int(trnAssignIterStr) == trnAssignIter:
            routelinkFile.close()
            criteriaMet = bool(int(criteriaMetStr))
            print "RouteLinkMSALog criteria %s met for %s iteration %d" % ("" if criteriaMet else "not ", timeperiod, trnAssignIter)
            return criteriaMet
    
    routelinkFile.close()
    print "Line not found for %s iteration %d in RouteLinkMSALog.csv!" % (timeperiod, trnAssignIter)
    raise

def readExtraDelayFile(extraDelayFile):
    """
    Read the extra delay file.  It should be of the format:
    LINE_NAMES,STOP,DELAY_AM,DELAY_MD,DELAY_PM,DELAY_EV,DELAY_EA
    
    The LINE_NAMES column is space-delimited.  The delays are in minutes.
    
    Returns a lookup dictionary: { (line name, stop, timeperiod):delay_in_mins }
    """
    try:
        extraDelayReader = csv.reader(open(extraDelayFile))
        extraDelayMapping = {}
        for line_names,stop,delay_am,delay_md,delay_pm,delay_ev,delay_ea in extraDelayReader:
            # header
            if line_names == "LINE_NAMES":
                continue
            
            if line_names.find(" ") >= 0:
                line_name_arr = line_names.split(" ")
            else:
                line_name_arr = [line_names]
            
            for line_name in line_name_arr:
                extraDelayMapping[(line_name, int(stop), "AM")] = float(delay_am)
                extraDelayMapping[(line_name, int(stop), "MD")] = float(delay_md)
                extraDelayMapping[(line_name, int(stop), "PM")] = float(delay_pm)
                extraDelayMapping[(line_name, int(stop), "EV")] = float(delay_ev)
                extraDelayMapping[(line_name, int(stop), "EA")] = float(delay_ea)
    
        WranglerLogger.debug("Read extra delay mapping: %s" % str(extraDelayMapping))
        return extraDelayMapping

    except Exception as e:
        WranglerLogger.fatal("Exception occurred:")
        WranglerLogger.fatal(e)
        WranglerLogger.fatal(traceback.format_exc())
        sys.exit(2)

def addExtraDelayToNet(extraDelayMapping, net, timeperiod):
    """
    Adds the given extraDelay to the net, assuming the given timeperiod
    """
    for line in net:
        for nodeIdx in range(len(line.n)):
            if (line.name, abs(int(line.n[nodeIdx].num)), timeperiod) in extraDelayMapping:
                curDelay = 0.0
                if "DELAY" in line.n[nodeIdx].attr:
                    curDelay = float(line.n[nodeIdx].attr["DELAY"])
                line.n[nodeIdx].attr["DELAY"] = "%.3f" % (curDelay + extraDelayMapping[(line.name, abs(int(line.n[nodeIdx].num)), timeperiod)])
        
def subtractExtraDelayToNet(extraDelayMapping, net, timeperiod):
    """
    Subtracts out the given extraDelay from the net, assuming the given timeperiod
    """
    for line in net:
        for nodeIdx in range(len(line.n)):
            if (line.name, abs(int(line.n[nodeIdx].num)), timeperiod) in extraDelayMapping:
                curDelay = 0.0
                if "DELAY" in line.n[nodeIdx].attr:
                    curDelay = float(line.n[nodeIdx].attr["DELAY"])
                assert (curDelay - extraDelayMapping[(line.name, abs(int(line.n[nodeIdx].num)), timeperiod)])>=0
                line.n[nodeIdx].attr["DELAY"] = "%.3f" % (curDelay - extraDelayMapping[(line.name, abs(int(line.n[nodeIdx].num)), timeperiod)])
           
                
if __name__ == '__main__':

    if (sys.argv[1].lower() == "postproc"):
        stripTimeFacRunTimeAttrs = False
    elif (sys.argv[1].lower() == "normal"):
        # TODO: CHAMP sets to true
        # For now, we'll leave this off.
        stripTimeFacRunTimeAttrs = False
    else:
        print USAGE
        exit(2)

    runmode = sys.argv[3]
    if runmode not in ("Simple", "Complex"):
        print USAGE
        exit(2)


    if sys.argv[2].lower() == "noextradelay":
        extraDelayMapping = None
    else:
        if runmode == "Simple":
            extraDelayMapping = readExtraDelayFile(sys.argv[2])
        else:
            extraDelayMapping = readExtraDelayFile(os.path.join("..",sys.argv[2]))
    
    complexArgnum = 4
    if runmode == "Complex":
        complexArgnum = 8
    if sys.argv[complexArgnum].lower() != "complexdwell":
        print USAGE
        exit(2)
        
    complexDwellModes = sys.argv[complexArgnum+1:]
    complexAccessModes = []
    noDwellModes = False
    for idx in range(len(complexDwellModes)):
        if complexDwellModes[idx].lower() == "complexaccess":
             complexAccessModes = complexDwellModes[idx+1:]
             complexDwellModes  = complexDwellModes[:idx]
             break
        elif complexDwellModes[idx].lower() == "none":
            noDwellModes = True  # save for later; we need to preserve index
        else:
            complexDwellModes[idx] = int(complexDwellModes[idx])

    if noDwellModes: complexDwellModes = []

    if len(complexAccessModes)==1 and complexAccessModes[0].lower() == "none":
        complexAccessModes = []
    else:
        for idx in range(len(complexAccessModes)):
            complexAccessModes[idx] = int(complexAccessModes[idx])
    
    if runmode == "Simple":

        # the convention is to run scripts from the model directory, but we would prefer to output into trn
        # so cd into there
        os.chdir("trn")

        setupLogging(infoLogFilename=None, debugLogFilename="transitDwellAccess_SimpleLog.txt", logToConsole=False)
        WranglerLogger.debug("complexDwellModes  = %s" % str(complexDwellModes))
        WranglerLogger.debug("complexAccessModes = %s" % str(complexAccessModes))
    
        for timeperiod in ["AM", "MD", "PM", "EV", "EA"]:
            net = TransitNetwork(modelType="TravelModelOne", modelVersion=1.0)
            
            try:
                net.parseFile(fullfile="transit_duplicated_stops_removed_new.lin",insert_replace=True)
            
                # Cube will fail on a line with no frequencies so let's just delete those ahead of time
                for lineidx in xrange(len(net.lines)-1, -1, -1):
                    if not isinstance(net.lines[lineidx],TransitLine): continue
                    frequency = net.lines[lineidx].getFreqs()
                    #print(frequency)
                    freqsum = sum([float(i) for i in frequency])
                    if freqsum == 0:
                        WranglerLogger.info("Line %s has no frequencies: %s -- deleting" % (net.lines[lineidx].name, str(net.lines[lineidx].getFreqs())))
                        del net.lines[lineidx]
                               
                TransitNetwork.initializeTransitCapacity(directory=".")
                net.addDelay(timeperiod="Simple", additionalLinkFile=None,
                             complexDelayModes=complexDwellModes, complexAccessModes=complexAccessModes,
                             stripTimeFacRunTimeAttrs=stripTimeFacRunTimeAttrs)

                # add the special fixed delays
                if extraDelayMapping:
                    addExtraDelayToNet(extraDelayMapping, net, timeperiod)

                cubeFile = os.path.abspath( os.path.join("hwy","complete_network_base.NET") )
                net.write(name='transitOriginal' + timeperiod, writeEmptyFiles=False, suppressQuery=True, suppressValidation=True, cubeNetFileForValidation=None)
                
            except:
                print "Unexpected error:"
                print traceback.print_exc()
                sys.exit(2)

            # convenience method to check that we know capacities for the complexModes
            if not net.checkCapacityConfiguration(complexDwellModes, complexAccessModes):
                exit(2)
      
            # Additionally outputs transitVehicleVolsOnLink[timeperiod].dbf for assignment to the roadway network,
            # with A,B,TRNVEHVOL attributes. 
            AB_to_trnvehvol = defaultdict(float)
            for line in net:              
                trnvehvol = line.vehiclesPerPeriod(timeperiod, Network.MODEL_TYPE_TM1)
                if trnvehvol == 0: continue
                
                prevStop = None
                for stop in line:
                    if prevStop: AB_to_trnvehvol[(prevStop, abs(stop))] += trnvehvol
                    prevStop = abs(stop)
            
            outTable = DataTable(numRecords=len(AB_to_trnvehvol),
                                 header=(FieldType("A", "N", 7, 0),
                                         FieldType("B", "N", 7, 0),
                                         FieldType("AB","C", 15, 0),
                                         FieldType("TRNVEHVOL", "F", 9, 2)))
            rownum = 0
            for key,val in AB_to_trnvehvol.iteritems():
                outTable[rownum]["A"] = key[0]
                outTable[rownum]["B"] = key[1]
                outTable[rownum]["AB"] = "%d %d" % (key[0], key[1])
                outTable[rownum]["TRNVEHVOL"] = val
                rownum += 1
            outfile = "transitVehicleVolsOnLink%s.dbf" % timeperiod
            outTable.writeAsDbf(outfile)
            WranglerLogger.info("Wrote %s with %d rows" % (outfile, len(AB_to_trnvehvol)))
                    
        exit(0)

    
    # Complex mode
    if len(sys.argv) <= 7:
        print USAGE
        print sys.argv
        exit(1)
    
    timeperiod      = sys.argv[4]
    trnAssignIter   = int(sys.argv[5])
    PHTDiffCond     = float(sys.argv[6])
    maxTrnAssignIter= int(sys.argv[7])
    
    # argument validation
    if timeperiod not in ("AM", "MD", "PM", "EV", "EA"):
        print "Invalid time period"
        print USAGE
        exit(1)
    
    setupLogging(infoLogFilename=None, debugLogFilename="transitDwellAccess_%s.%d.log" % (timeperiod, trnAssignIter), 
                 logToConsole=False)

    WranglerLogger.info("runmode            = {}".format(runmode))
    WranglerLogger.info("trnAssignIter      = {}".format(trnAssignIter))
    WranglerLogger.info("PHTDiffCond        = {}".format(PHTDiffCond))
    WranglerLogger.info("maxTrnAssignIter   = {}".format(maxTrnAssignIter))
    WranglerLogger.info("complexDwellModes  = {}".format(complexDwellModes))
    WranglerLogger.info("complexAccessModes = {}".format(complexAccessModes))

    # check if end criteria met either via PHT or MSA Volumes
    criteriaMet = updatePHT(timeperiod, trnAssignIter, maxTrnAssignIter, PHTDiffCond)
        
    if PHTDiffCond==0:
        criteriaMet = (trnAssignIter>=maxTrnAssignIter) or checkMSAcriteriaMet(timeperiod, trnAssignIter)
        
    # MINIMUM iterations = 4
    if (len(complexDwellModes)>0 or len(complexAccessModes)>0) and trnAssignIter < 4:
        criteriaMet = False
        
    # Update stats and logs and such, and write a new network file *if not criteriaMet*
    MSAnet      = None
    MSAweight   = 0.0
    tad         = None
    nextNetFile  = "transit%s_%d" % (timeperiod, trnAssignIter+1)
    
    # give a header to the log files
    if trnAssignIter == 0:
        logfile = open("lineStats"+timeperiod+".csv", "w")
        logfile.write("iteration,line,totalDwell,noBoardStops\n")
        logfile.close()
        
        logfile = open("dwellbucket"+timeperiod+".csv", "w")
        logfile.write("iteration,bucketnum,bucketcount\n")
        logfile.close()
        
    # We have boards, alights etc on which to compute more sophisticated dwells
    curNetFile  = "transit%s_%d.lin" % (timeperiod, trnAssignIter)
    MSAweight   = 1.0/float(trnAssignIter+1)
    curSubdir   = "Subdir"+str(trnAssignIter)
    origNetFile = os.path.join("..", "transitOriginal%s.lin" % timeperiod)
    
    # No PHT condition must mean we're using volume conditions so use the MSA'd
    # assignment we already have
    if PHTDiffCond==0:
        curRouteFileName       = os.path.join(curSubdir, "trnlink{}_ALLMSA.dbf".format(timeperiod))
    else:
        curRouteFileName       = None

    WranglerLogger.info("curRouteFileName   = {}".format(curRouteFileName))
        
    TransitNetwork.initializeTransitCapacity(directory="..")
    tad = None
    try:
        tad = TransitAssignmentData(timeperiod=timeperiod,
                                    modelType=Network.MODEL_TYPE_TM1,
                                    ignoreModes=[1,2,3,4,5,6,7],
                                    tpfactor="constant_with_peaked_muni",
                                    transitCapacity=TransitNetwork.capacity,
                                    lineLevelAggregateFilename=curRouteFileName)
    except Exception, err:
        WranglerLogger.fatal(sys.exc_info()[0])
        WranglerLogger.fatal(sys.exc_info()[1])
        WranglerLogger.fatal(traceback.format_exc())
        sys.exit(2)

    # since we've aggregated, write it out
    if not curRouteFileName:
        tad.writeDbfs(os.path.join(curSubdir, "trnlink{}_ALL.dbf".format(timeperiod)))
        
    currentNet = TransitNetwork(modelType=Network.MODEL_TYPE_TM1, modelVersion=1.5)
    currentNet.parseFile(fullfile=curNetFile)
    originalNet = TransitNetwork(modelType=Network.MODEL_TYPE_TM1, modelVersion=1.5)
    originalNet.parseFile(fullfile=origNetFile)

    # remove out the extra delay so it doesn't get MSA'd in with dwells
    if extraDelayMapping:
        subtractExtraDelayToNet(extraDelayMapping, currentNet, timeperiod)
    
    # report on lines of interest - note that it does not have extraDelay
    updateLinesOfInterest(timeperiod, trnAssignIter, complexAccessModes, currentTad=tad, currentNet=currentNet)
    
    if not criteriaMet:
        originalNet.addDelay(timeperiod=timeperiod, 
                             additionalLinkFile=os.path.join("..","transitLines.link"),
                             transitAssignmentData=tad,
                             complexDelayModes=complexDwellModes,
                             complexAccessModes=complexAccessModes,
                             MSAweight=MSAweight,
                             previousNet=currentNet,
                             logPrefix=str(trnAssignIter),
                             stripTimeFacRunTimeAttrs=stripTimeFacRunTimeAttrs)
    
        # add the special fixed delays
        if extraDelayMapping:
            addExtraDelayToNet(extraDelayMapping, originalNet, timeperiod)    
    
    # If the end criteria is met, we're done.  Signify by *not* writing new transit file
    if criteriaMet:
        WranglerLogger.info("Criteria met for %s in transit assignment iteration %d" % (timeperiod, trnAssignIter))
        exit(0)

    originalNet.write(name=nextNetFile, writeEmptyFiles=False,suppressQuery=True,suppressValidation=True)
    WranglerLogger.info("Wrote {}".format(nextNetFile))
