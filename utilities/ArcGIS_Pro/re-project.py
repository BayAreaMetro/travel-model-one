import arcpy

# input data is in some other coordinate system, e.g. GCS_North_American_1983
input_features = r"M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT\metrics\PHED\UZA_select\UZA_select.shp"

# output data
output_feature_class = r"M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT\metrics\PHED\UZA_select\FiveUZA_NAD1983UTMzone10N.shp"

# create a spatial reference object for the output coordinate system
out_coordinate_system = arcpy.SpatialReference("NAD 1983 UTM Zone 10N")

# run the tool
arcpy.Project_management(input_features, output_feature_class, out_coordinate_system)
