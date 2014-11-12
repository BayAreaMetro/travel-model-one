
joinIndivIncome_iter1.job - Attach income to individual trips
- Reads main\IndivTripData_1.csv and main\householdData_1.csv
  and attaches the income from the households to individual trips, 
  output as main\IndivTripDataIncome.csv

joinJointIncome_iter1.job - Attach income to joint trips
- Reads main\JointTripData_1.csv and main\householdData_1.csv
  and attaches the income from the households to joint trips,
  output as main\JointTripDataIncome.csv

prepAssignIncome.job - Convert trip tables into time/income/mode OD matrices
- Copies trip tables main\(indiv|joint)TripDataIncome.csv to 5 timeperiod-copies:
  main\(indiv|joint)TripData_temp_(EA|AM|MD|PM|EV).csv so Cube can do time periods in parallel
- step one: convert individual trip list to an origin/destination list. 
  Foreach time period
  + Read main\IndivTripData_temp_@token_period@.csv
  + Tally trips by OD and incQ in one array per trip mode (da,datoll,sr2,... end with 15 transit)
  + Write main\IndivTrips(EA|AM|MD|PM|EV)inc[1-4].dat with
    o,d,da,datoll,...  trips for that o,d,income, mode
- step two: convert joint trip list to an origin/destination list
  Same as Indiv but increments by num_participants
- step three: convert the fixed format files to tp+ matrices
  + Reads the output from the previous steps, combines them, scales them up by sampleshare
    and outputs main\trips(EA|AM|MD|PM|EV)inc[1-4].tpp
  + Rolls up main\trips(EA|AM|MD|PM|EV)inc[1-4].tpp into main\trips(EA|AM|MD|PM|EV).tpp

RunMetrics.bat
- runs metrics\Matrix_Computation.job
  + Reads trip tables, trips(EA|AM|MD|PM|EV).tpp and transit skims, 
    outputs csv metrics\all_metrics.csv:
     "Name","Transit Trips", "In-vehicle hours ","Out-of-vehicle hours", "Init wait hours ","Xfer wait hours","Walk acc & egr hours","Aux walk hours","Drive acc & egr hours"
    where Name is one '(wlk|drv)_(com|hvy|exp|lrf|loc)_(wlk_drv)'
    So 15 rows (3 acc/egr x 5 transit mode categories)
  
  + Reads income-based trip tables, trips(EA|AM|MD|PM|EV)inc[1-4].tpp and transit skims,
    appends rows:
     "Mode","Income","Daily Trips","Avg Time","Avg Cost"
     with Mode (com|hvy|exp|lrf|loc), Income inc[1-4]

  + Reads income-based trip tables, trips(EA|AM|MD|PM|EV)inc[1-4].tpp and hwy skims,
    appends rows:
    "Mode","Income","Daily Trips","Avg Time","Avg Dist","Avg Cost"
    With Mode (da|sr2|sr3)(toll?), Income inc[1-4]

  + Reads income-based trip tables, trips(EA|AM|MD|PM|EV)inc[1-4].tpp and
    nonmotorized skims, appends rows:
    "Mode","Income","Daily Trips","Avg Time", "Avg Dist"
    With Mode (Walk|Bike)

- runs hwynet.py:
  python metrics\hwynet.py hwy/iter%ITER%/avgLoad5period.csv metrics metrics/all_metrics.csv a
  
  Reads avgLoad5period.csv, the text-based version of the network (which incidentally has more
  fields than I'm seeing, like vol_DA, vol_S2, ... vol_HVT.  I see them in the .net but not in the .csv...)

  Sums by timeperiod and class ('DA','S2','S3','SM','HV','DAT','S2T','S3T','SMT','HVT'), the
   + Vehicle Hours Traveled
   + Vehicle Miles Traveled
   + Hypothetical FFT by class and period (fft x volume) - in minutes
  Sums Hours of Non-recurring delay via nonRecurringDelayLookup.csv which is by v/c
  Sums Collisions per day by summing VMT by at,ft,#lanes, and using collisionLookup.csv
    which maps those tuples to collisions per vmt for different collision types
  Sums Emissions by summing VMT by timeperiod,class(car,smalltruck,heavytruck) and speed
    and using emissionsLookup.csv which maps those tuples to different types of emissions

- runs quickboards

- runs transit.py
  python metrics\transit.py trn/quickboards.xls metrics/all_metrics.csv a

  + Translates line name to mode (Local|Express|Ferry|Light Rail|Heavy Rail|Commuter Rail)
  + Sums daily boardings and passenger miles by mode
  + Appends to our buddy, all_metrics.csv


  Example output:
  X:\Archived Applications\Travel Model One\RTP 2013\Projects\_PB Metric Calc Files\Project Directory Folder\metrics  (where X: is \\mtccloud\cloudmodels1)