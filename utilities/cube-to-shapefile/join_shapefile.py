USAGE = """
 Use arcpy to do simple join for two shapefiles.
"""

import argparse, os, sys
import arcpy

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("in_shapefile1", help="Input Shapefile 1")
    parser.add_argument("in_shapefile2", help="Input Shapefile 2")
    parser.add_argument("out_shapefile", help="Output Shapefile")
    parser.add_argument("join_field", help="Join field")

    args = parser.parse_args()

    print(args)

    print("Using scratchGDB as workspace: {}".format(arcpy.env.scratchGDB))
    arcpy.env.workspace = arcpy.env.scratchGDB
    print(arcpy.env.workspace)

    in_shapefile1 = os.path.abspath(args.in_shapefile1)
    in_shapefile2 = os.path.abspath(args.in_shapefile2)
    out_shapefile = os.path.abspath(args.out_shapefile)

    # copy features to workspace gdb because joining shapefiles results in unusable column names
    INPUT_SHAPE1 = "in_shape1"
    if arcpy.Exists(os.path.join(arcpy.env.workspace, INPUT_SHAPE1)):
        arcpy.Delete_management(os.path.join(arcpy.env.workspace, INPUT_SHAPE1))
    arcpy.CopyFeatures_management(
        in_shapefile1, os.path.join(arcpy.env.workspace, INPUT_SHAPE1)
    )
    result = arcpy.GetCount_management(INPUT_SHAPE1)
    print("Copied {} into workspace; {} rows".format(args.in_shapefile1, result[0]))

    INPUT_SHAPE2 = "in_shape2"
    if arcpy.Exists(os.path.join(arcpy.env.workspace, INPUT_SHAPE2)):
        arcpy.Delete_management(os.path.join(arcpy.env.workspace, INPUT_SHAPE2))
    arcpy.CopyFeatures_management(in_shapefile2, INPUT_SHAPE2)
    result = arcpy.GetCount_management(INPUT_SHAPE2)
    print("Copied {} into workspace; {} rows".format(args.in_shapefile2, result[0]))

    # do the join
    joined_table = arcpy.AddJoin_management(
        INPUT_SHAPE1, args.join_field, INPUT_SHAPE2, args.join_field
    )
    OUT_FC = "out_fc"
    if arcpy.Exists(os.path.join(arcpy.env.workspace, OUT_FC)):
        arcpy.Delete_management(os.path.join(arcpy.env.workspace, OUT_FC))

    # save it
    arcpy.CopyFeatures_management(joined_table, OUT_FC)
    result = arcpy.GetCount_management(OUT_FC)
    print("Saved as {}; {} rows".format(OUT_FC, result[0]))

    fields = arcpy.ListFields(OUT_FC)
    for field in fields:

        new_name = field.name

        # rename from in_shap1_XXX to XXX1
        if field.name.startswith(INPUT_SHAPE1):
            new_name = field.name[len(INPUT_SHAPE1) + 1 :]
            # length must be 9 or less
            if len(new_name) > 9:
                new_name = new_name[:9]
            new_name = new_name + "1"
        elif field.name.startswith(INPUT_SHAPE2):
            new_name = field.name[len(INPUT_SHAPE2) + 1 :]
            # length must be 9 or less
            if len(new_name) > 9:
                new_name = new_name[:9]
            new_name = new_name + "2"

        print(
            "{}: {} => {} is a type of {} with a length of {}".format(
                OUT_FC, field.name, new_name, field.type, field.length
            )
        )

        arcpy.AlterField_management(OUT_FC, field=field.name, new_field_name=new_name)

    arcpy.CopyFeatures_management(OUT_FC, out_shapefile)
    print("Wrote {}".format(out_shapefile))
