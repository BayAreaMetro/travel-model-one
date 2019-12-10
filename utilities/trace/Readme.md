
## Directions for logsums dummy household trace

#### 1) move the logs dir aside so we don't overwrite; I usually save as logs_pretrace
#### 2) create logsums_trace dir for output
#### 3) create trace version of logsums.properties file; I usually save old version as logums.properties_pretrace

note: if running on different machine than originally run, may need to 
- set model_year nd host_ip_address
- then execute this to fix IPs: python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --logsums

#### 4) make necessary changes to CTRAMP\runtime\logsums.properties file:

set output files to be in logsums_trace
  e.g. Results.HouseholdDataFile = logsums_trace/householdData.csv

ditto for show pricing 

UsualWorkAndSchoolLocationChoice.ShadowPricing.OutputFile   = logsums_trace/ShadowPricing.csv
UsualWorkAndSchoolLocationChoice.SizeTerms.OutputFile       = logsums_trace/DestinationChoiceSizeTerms.csv

turn on trace household and set to only do that household

#-- Set to the ID(s) of any household to write out trace information
Debug.Trace.HouseholdIdList=1234

#-- Set to the ID of a single household to run the simulation with
run.this.household.only=1234

### 4) turn on the logging

edit CTRAMP\runtime\config\log4j-node0.xml

for mandatory logging, turn level value of tourDCMan to debug:

    <logger name="tourDcMan" additivity="false">
        <level value="debug"/>
        <appender-ref ref="TourDCMan-FILE"/>
    </logger>

for nonmandatory logging, turn level of tourDcNonMan to debug:

    <logger name="tourDcNonMan" additivity="false">
        <level value="debug"/>
        <appender-ref ref="TourDCNonMan-FILE"/>
    </logger>


 ### 5) create trace version of RunLogsums.bat; I usually call it RunLogsums_trace.bat

diffs:

It should still SetPath and set the HOST_IP_ADDRESS
drop all the other stuff up and start at

echo STARTED LOGSUMS RUN

delete after shutting down java

### 6) RunLogsums_trace.bat; it won't take too long (~10 min?  should time)

It will produce gigantic event-node0-tourDCMan.log (or nonman version) -- more than 1GB 

Run parse_ctramp_logs.py file in this directory to parse that log out
(Note that python 3 is needed because of the regex)

Then the resulting csv files can be viewed (base and build) with logsum_trace.twb

