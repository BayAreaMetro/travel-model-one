# DefineProjection example (Python window)

import arcpy

infc = r"C:\Users\ftsang\Documents\ArcGIS\projects\TIP_UA\2020.shp"
sr = arcpy.SpatialReference("NAD 1983 UTM Zone 10N")
arcpy.DefineProjection_management(infc, sr)
