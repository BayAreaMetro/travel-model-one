--------------------
# Overview
-------------------

This directory includes: 
- legacy tools that are no longer used in TM1.5 and subsequent model release
- tools for processing express lane "Trip Transaction reports" obtained from MTC's express lane team

--------------------
# Legacy tools from 2015
-------------------
These include:
* Summarize Express Lane Prices.Rmd
* express-lane-prices.Rproj
* extract-express-lane-data.bat
* extract-express-lane-data.job

--------------------
# Tools for processing express lane "Trip Transaction reports"
--------------------
In Nov 2023, we calcualted express lane toll per mile using the following materials from Bay Area Toll Authority (BATA)

--------------------
INPUTS
--------------------
- March 2023 Express Lane Trip data, including SM-101, I-880, and I-680
- Information of each Read Point (All RPLong Lat.xls0, which contains coordinate system of each read point
- A google map of read points: https://www.google.com/maps/d/edit?mid=12jxQhxJTe41ACAHvugHjLOXGzGmuBR8&usp=sharing

--------------------
TOOLS
--------------------
Using the above data, we calculated express lane toll per mile at the segment level using Google Distance API by a R script.
- Google Distance API: https://developers.google.com/maps/documentation/distance-matrix/overview
- R package implementing Google Distance API (gmapsdistance): https://cran.r-project.org/web/packages/gmapsdistance/readme/README.html
- Sample R scripts implementing Google Distance API: https://jul-carras.github.io/2019/01/19/ggmap_distances/

--------------------
METHODS & OUTPUTS
--------------------
1. Get Google Distance API from https://developers.google.com/maps/documentation/distance-matrix
2. Run R Scripts Travel_dist_GoogleAPI.R. The input of the script is the EL trip data received from BATA
3. The output is the trip data received from BATA with an additional column indicating the travel distance: CorridorName_dist.csv
4. Bring the outputs (CorridorName_dist.csv) to Tableau EL_Pricing_Data_March_2023.twb. 
5. Tableau sheets 'Toll Per Mile Corridor', 'Toll Per Mile Zone', and 'Toll Per Mile Segment' can be used at different level
6. Tableau sheets 'Toll Per Mile Zone' and 'Toll Per Mile Segment' only uses single zone (or same segment) trips.
7. For the purpose of the Asana task we are working on (https://app.asana.com/0/0/1205854882001800/f), we used 'Toll Per Mile Segment' since most trips are single-segment trips
8. Then, we grouped network cube links to segments, made a crosswalk between links and segments: EL_Segment_crosswalk.csv
9. Each segment is treated as a TOLLCLASS, so we updated links' tollclass with their segment information: see network project 'EXP_ObservedPrices_2023', and the toll.csv of it.

