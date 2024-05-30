USAGE = """

 Utility script to aggregate data from different custom activity templates across years.

"""

import argparse, pathlib, sys
import openpyxl
import openpyxl.utils.dataframe
import pandas as pd

SHEET_NAMES = ["Daily_VMT_By_Veh_Tech","Hourly_Fraction_Veh_Tech_Speed"]

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--emfac_version",  required=True, choices=['2014','2021'])
    parser.add_argument("--sb375",          action='store_true', help="For 'Custom Hourly Speed Fractions' checkbox")
    args = parser.parse_args()

    template_dir = pathlib.Path(__file__).parent / "Custom_Activity_Templates"
    print(f"{template_dir=}")

    suffix_sb375 = "_SB375" if args.sb375 else ""
    glob_str = f"E{args.emfac_version}_emissions_MPO-MTC_*_annual_VMTbyVehFuelType_CustSpeed{suffix_sb375}.xlsx"
    print(f"{glob_str=}")
    template_list = sorted(template_dir.glob(glob_str))
    # print(f"{template_list=}")
    if len(template_list) == 0:
        print(f"No templates found for {glob_str}")
        sys.exit(1)

    dataframes = {}
    for template_file in template_list:
        print(f"Reading {template_file}")
        for sheet_name in SHEET_NAMES:
            sheet_df = pd.read_excel(template_file, sheet_name=sheet_name)

            # concatenate
            if sheet_name not in dataframes.keys():
                dataframes[sheet_name] = sheet_df
            else:
                dataframes[sheet_name] = pd.concat([dataframes[sheet_name], sheet_df])

    # save as csv
    outfile = f"E{args.emfac_version}_emissions_MPO-MTC_allyears_annual_VMTbyVehFuelType_CustSpeed{suffix_sb375}.xlsx"
    wb = openpyxl.Workbook()

    first_sheet = True
    for sheet_name in SHEET_NAMES:
        print(f"Creating {sheet_name}; columns: {dataframes[sheet_name].columns}")
        if first_sheet:
            ws = wb.active
            ws.title = sheet_name
            first_sheet = False

        else:
            ws = wb.create_sheet(sheet_name)

        for r in openpyxl.utils.dataframe.dataframe_to_rows(
            dataframes[sheet_name], index=False, header=True):
            ws.append(r)

    wb.save(outfile)
    print(f"Saved {outfile}")