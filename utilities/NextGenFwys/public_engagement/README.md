# Process to Produce Driven and Transit Path Maps

As part of the second round of engagement for the [Next Generation Freeways Study](https://github.com/BayAreaMetro/travel-model-one/tree/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys) (also known as NGFS), maps were produced to show metrics such as travel times and costs for sample trips between Origin Destination pairs that were predetermined from responses from the focus group intake surveys. Below are the steps necessary to reproduce the outputs.

## Steps:
* produce a new list of OD pairs
    * currently a manual process
        * List of Origin and Destination TAZs are selected using GIS software to visualize the geographic locations desired (assumes a list of zip codes is ready, can also use [this tableau](https://10ay.online.tableau.com/#/site/metropolitantransportationcommission/workbooks/1332814?:origin=card_share_link) to pick TAZs)
        * It's helpful to have a layer that includes geometries for zip codes to better locate the relevant TAZs
        * Both the [TAZ layer](https://arcg.is/1iS08u) as well as one for [California zip codes](https://gis.data.ca.gov/maps/CDEGIS::california-zip-codes) can be found online
    * Note that for the purposes of [`TransitAssign_NGFtrace.job`](https://github.com/BayAreaMetro/travel-model-one/blob/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys/public_engagement/TransitAssign_NGFtrace.job), the O/D lists can be a maximum of 55 Origins or Destinations which cannot exceed 255 characters in length
* Update the list of O/Ds in [`TransitAssign_NGFtrace.job`](https://github.com/BayAreaMetro/travel-model-one/blob/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys/public_engagement/TransitAssign_NGFtrace.job) and [`TraceDApaths.bat`](https://github.com/BayAreaMetro/travel-model-one/blob/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys/public_engagement/TraceDApaths.bat) located on [`X:\travel-model-one-master\utilities\NextGenFwys\public_engagement`](https://github.com/BayAreaMetro/travel-model-one/tree/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys/public_engagement)
    * [`TransitAssign_NGFtrace.job`](https://github.com/BayAreaMetro/travel-model-one/blob/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys/public_engagement/TransitAssign_NGFtrace.job) 
        * update variables `token_debug_origin_list` & `token_debug_destination_list`
    * [`TraceDApaths.bat`](https://github.com/BayAreaMetro/travel-model-one/blob/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys/public_engagement/TraceDApaths.bat)
        * update variables `ORIGIN` & `DESTINATION`
    * Note that this step can be avoided by updating the relevant scripts to check for O/D lists passed in the command line as arguments as part of [`UpdateMapDataForNewOD.bat`](https://github.com/BayAreaMetro/travel-model-one/blob/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys/public_engagement/UpdateMapDataForNewOD.bat) (an area for future improvement).
* run [`UpdateMapDataForNewOD.bat`](https://github.com/BayAreaMetro/travel-model-one/blob/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys/public_engagement/UpdateMapDataForNewOD.bat) on a modeling server to generate the driven and transit trace paths
    * first verify the desired model runs in the script
    * update paths based on mapped drives on respective modeling server being used to run the batch file
    * Other steps included in this script:
        * clean the driven and transit trace paths
            * driven
                * copy [`HwyAssign_trace_to_csv.py`](https://github.com/BayAreaMetro/travel-model-one/blob/551f55aa064123c94b9b23761dc342b398bede0f/utilities/NextGenFwys/public_engagement/HwyAssign_trace_to_csv.py) to the relevant HwyAssign_trace folder and run it from there
                    * (done as part of [`UpdateMapDataForNewOD.bat`](https://github.com/BayAreaMetro/travel-model-one/blob/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys/public_engagement/UpdateMapDataForNewOD.bat))
            * transit
                * run [`Convert_lin_to_csv.py`](https://github.com/BayAreaMetro/travel-model-one/blob/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys/public_engagement/Convert_lin_to_csv.py) to produce individual ab link tables for all transit lines contained in transitLines.lin
                    * these lookup tables are used in [`Convert_PRN_to_CSV.py`](https://github.com/BayAreaMetro/travel-model-one/blob/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys/public_engagement/Convert_PRN_to_CSV.py) 
                * clean the output trace files (.PRN) by running [`Convert_PRN_to_CSV.py`](https://github.com/BayAreaMetro/travel-model-one/blob/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys/public_engagement/Convert_PRN_to_CSV.py) 
                    * detailed breakdowns of transit routes used as well as relevant link node information for most OD pairs are extracted from the trace files
        * find the transit fares associated with the OD trips
            * run [`Lookup_transit_fare_using_OD_pairs_and_modes.py`](https://github.com/BayAreaMetro/travel-model-one/blob/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys/public_engagement/Lookup_transit_fare_using_OD_pairs_and_modes.py)
                * this script iterates through a list of pathways and reads trnskmam tables for various mode combinations to find the transit fare cost of an OD trip
        * produce lists of Origins and Destinations for the drive to transit portions of the various traced paths.
            * Driven paths would need to be produced for the new lists of Origins and Destinations using [`TraceDApaths.bat`](https://github.com/BayAreaMetro/travel-model-one/blob/f37a3befc2e2d53d32054a17fde218c641f0b7f8/utilities/NextGenFwys/public_engagement/TraceDApaths.bat) (see above for instructions)