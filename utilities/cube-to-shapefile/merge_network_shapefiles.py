USAGE = """

Merge (e.g. concatenate) network shapefiles from two different directories into a single shapefile via arcpy.
Assumes that the shapefiles have the same fields.

"""

import argparse, os, sys
import arcpy

# shapefiles to merge
SHAPEFILES = [
    "network_links.shp",
    "network_nodes.shp",
    "network_trn_lines.shp",
    "network_trn_links.shp",
    "network_trn_stops.shp",
    "trnlinkam_withSupport.shp",
    "trnlinkpm_withSupport.shp",
]

if __name__ == "__main__":
    WORKING_DIR = os.getcwd()

    parser = argparse.ArgumentParser(
        description=USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("indir1", help="Input directory 1")
    parser.add_argument("indir2", help="Input directory 2")
    parser.add_argument("outdir", help="Output directory")
    args = parser.parse_args()

    arcpy.env.workspace = WORKING_DIR

    for shapefile in SHAPEFILES:
        infile1 = os.path.join(args.indir1, shapefile)
        infile2 = os.path.join(args.indir2, shapefile)
        outfile = os.path.join(args.outdir, shapefile)

        print("infile1: {}".format(infile1))
        print("infile2: {}".format(infile2))
        print("outfile: {}".format(outfile))

        if not arcpy.Exists(infile1):
            print("{} doesn't exist -- skipping".format(infile1))
            continue

        if not arcpy.Exists(infile2):
            print("{} doesn't exist -- skipping".format(infile2))
            continue

        if arcpy.Exists(outfile):
            print("Found existing {} - deleting".format(outfile))
            arcpy.Delete_management(outfile)

        # Create FieldMappings object to manage merge output fields
        field_mappings = arcpy.FieldMappings()

        # Add all fields from both infile2
        infile1_fieldnames = [f.name for f in arcpy.ListFields(infile1)]
        infile2_fields = arcpy.ListFields(infile2)

        print(infile1_fieldnames)
        # print(infile2_fields)

        for field in infile2_fields:
            field_name = field.name
            if field_name in ["FID", "Shape"]:
                continue

            field_map = arcpy.FieldMap()

            if field_name in infile1_fieldnames:
                field_map.addInputField(infile1, field_name)
            field_map.addInputField(infile2, field_name)

            # define the resulting field based on infile2 definition
            out_field = arcpy.Field()
            out_field.name = field_name
            out_field.type = field.type
            out_field.length = field.length
            out_field.scale = field.scale
            out_field.precision = field.precision
            field_map.outputField = out_field

            print(
                "  field_map inputFieldCount={} mergeRule={} outputField.name=[{}] type={} length={}  field2.length={}".format(
                    field_map.inputFieldCount,
                    field_map.mergeRule,
                    field_map.outputField.name,
                    field_map.outputField.type,
                    field_map.outputField.length,
                    field.length,
                )
            )

            field_mappings.addFieldMap(field_map)

        arcpy.Merge_management(
            [infile1, infile2], outfile, field_mappings, add_source="ADD_SOURCE_INFO"
        )
