
The Tableau workbook, GHG_visualizer.twb, uses relative referencing.
It reads three files:
- avgload5period_vehclasses.csv to get link volumes and distances
- interpolated.csv to get emission rates 
- \core_summaries\VehicleMilesTraveled.csv to get total population.
 
For the relative referencing to work, the Tableau workbook is to be placed in the OUTPUT directory of a model run.

interpolated.csv needs to be copied from travel-model-one\utilities\RTP\Emissions\GHG_visualizer, and renamed to drop the year in the file name.
e.g. copy C:\Users\ftsang\Documents\GitHub\travel-model-one\utilities\RTP\Emissions\GHG_visualizer\interpolated_2015.csv interpolated.csv

When launched,  the Tableau workbook gives an error message about multiple connections, it is okay to ignore that error message.

If you make edits to the Tableau workbook and want to save the edits to the template, you'll need to absolute paths for three csv files listed above.