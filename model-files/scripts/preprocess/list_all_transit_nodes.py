import csv, glob, os, re, sys, traceback
from math import pow, sqrt
from collections import defaultdict

from Wrangler import setupLogging, Network, TransitLine, TransitNetwork, TransitAssignmentData, WranglerLogger
from dataTable import DataTable, FieldType
import numpy as np
import math
os.chdir("trn")
setupLogging(infoLogFilename=None, debugLogFilename="list_all_transit_nodes.txt", logToConsole=True)
net = TransitNetwork(modelType="TravelModelOne", modelVersion=1.0)

net.parseFile(fullfile="transit_duplicated_stops_removed.lin",insert_replace=True)
all_node_ids = []

for lineidx in xrange(len(net.lines)-1, -1, -1):
    if not isinstance(net.lines[lineidx],TransitLine): continue
    #if net.lines[lineidx].hasDuplicateStops():
    _stop_to_idx = {}
    _stop_list   = []
    all_nodes=net.lines[lineidx].listNodeIds(ignoreStops=False)
    for items in all_nodes:
        all_node_ids.append(str(items))
        
    #all_node_ids.append(net.lines[lineidx].listNodeIds(ignoreStops=False))
    for node in all_nodes:
        node_num=node             
        if node_num not in _stop_to_idx: 
            _stop_to_idx[node_num] = []
        _stop_to_idx[node_num].append(len(_stop_list))  
        _stop_list.append(np.int(node_num))
        
                

        #net.lines[lineidx].setNodes(_stop_list)

        
np.savetxt("all_transit_nodes.csv", 
           all_node_ids,
           delimiter =",", fmt='%s')

           