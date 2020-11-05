USAGE = """

  Joins network link shapefile to TAZ shapefile and determins correspondence between link => TAZ, portion of link
  Note that some links may span more than one TAZ.

  Output csv has the following columns:
  * A             = A node
  * B             = B node
  * TAZ1454       = taz
  * link_mi       = total link length in miles (calculated by arcpy so may differ from DISTANCE)
  * linktaz_mi    = link intersect this taz length in miles (calculated by arcpy)
  * linktaz_share = share of the link in this taz (e.g. linktaz_mi / link_mi)

  Requires arcpy, so use arcgis version of python
  e.g. set PATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3;C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\Scripts

  Developed for task: Calculate metrics for emissions and fatalities at TAZ level
  https://app.asana.com/0/13098083395690/1195902248890525/f

"""

import argparse, os
import arcpy
import numpy,pandas

TAZ_SHAPEFILE = "M:\\Data\\GIS layers\\TM1_taz\\bayarea_rtaz1454_rev1_WGS84.shp"

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description = USAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('link_shapefile',  type=str, help="Input link shapefile")
    parser.add_argument('link_to_taz_csv', type=str, help="Output link to taz csv")
    my_args = parser.parse_args()

    # use scratch gdb
    arcpy.env.workspace = arcpy.env.scratchGDB
    print("Using workspace {}".format(arcpy.env.workspace))

    # copy link shapefile into workspace
    link_feature = "network_links"
    if arcpy.Exists(link_feature):
        print("Found {}; deleting".format(link_feature))
        arcpy.Delete_management(link_feature)
    arcpy.CopyFeatures_management(my_args.link_shapefile, link_feature)
    result = arcpy.GetCount_management(link_feature)
    print("Copied {} into workspace; {} rows".format(my_args.link_shapefile, result[0]))

    # calculate link length
    length_field = "link_mi"
    arcpy.AddField_management(link_feature, length_field, "FLOAT", field_precision=12, field_scale=4)
    arcpy.CalculateGeometryAttributes_management(link_feature, [[length_field, "LENGTH"]], "MILES_US")

    # copy taz shapefile into workspace
    taz_feature = "tazs"
    if arcpy.Exists(taz_feature):
        print("Found {}; deleting".format(taz_feature))
        arcpy.Delete_management(taz_feature)
    arcpy.CopyFeatures_management(TAZ_SHAPEFILE, taz_feature)
    result = arcpy.GetCount_management(taz_feature)
    print("Copied {} into workspace; {} rows".format(TAZ_SHAPEFILE, result[0]))

    # intersect
    link_taz_feature = "link_intersect_taz"
    if arcpy.Exists(link_taz_feature):
        print("Found {}; deleting".format(link_taz_feature))
        arcpy.Delete_management(link_taz_feature)
    arcpy.Intersect_analysis([link_feature, taz_feature], link_taz_feature)
    result = arcpy.GetCount_management(link_taz_feature)
    print("Created intersect {}; {} rows".format(link_taz_feature, result[0]))

    # calculate length of these links
    length_taz_field = "linktaz_mi"
    arcpy.AddField_management(link_taz_feature, length_taz_field, "FLOAT", field_precision=12, field_scale=4)
    arcpy.CalculateGeometryAttributes_management(link_taz_feature, [[length_taz_field, "LENGTH"]], "MILES_US")

    # bring into pandas
    fields = ["A","B","TAZ1454",length_field,length_taz_field]
    links_array = arcpy.da.TableToNumPyArray(in_table=link_taz_feature, field_names=fields)
    links_df = pandas.DataFrame(links_array, columns=fields)

    # divide lengths to get proportion
    links_df["linktaz_share"] = links_df[length_taz_field]/links_df[length_field]
    print("links_df has {} rows; head:\n{}".format(len(links_df), links_df.head()))

    # write it
    links_df.to_csv(my_args.link_to_taz_csv, index=False)
    print("Wrote to {}".format(my_args.link_to_taz_csv))
