USAGE = """

python aggregateTransitLinks AM|MD|PM|EV|EA

 Aggregates the assignment files across submodes into trnlink[timeperiod].dbf

"""
import logging, sys
from pathlib import Path

# we only want to use this specific version of wrangler
libdir = Path(__file__).resolve().parent / ".." / ".." / "lib"
sys.path.insert(0, str(libdir))

from Wrangler import setupLogging, Network, TransitAssignmentData, TransitNetwork

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(USAGE)
        exit(1)

    timeperiod     = sys.argv[1]
    routeFileName  = f"trnlink{timeperiod}.dbf"

    setupLogging(infoLogFilename=None,
                 debugLogFilename=f"aggregateTransitLinks_{timeperiod}.log",
                 logToConsole=False)

    # Read in the current assignment
    logging.info("Reading in transit assignment data for " + timeperiod)
    TransitNetwork.initializeTransitCapacity(directory="..")
    curTad = TransitAssignmentData(
        timeperiod=timeperiod,
        modelType=Network.MODEL_TYPE_TM1,
        ignoreModes=[1,2,3,4,5,6,7],
        tpfactor="constant_with_peaked_muni",
        transitCapacity=TransitNetwork.capacity)

    # Write out the assignment
    curTad.writeDbfs(asgnFileName=routeFileName, aggregateFileName=None)