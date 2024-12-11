USAGE="""
  Reads the data files in M:\Data\BLS_StateAndAreaEmployment
  and converts to long form.
"""
import os, pathlib, sys, warnings
import pandas
import openpyxl

DATA_DIR = pathlib.Path("M:\\Data\\BLS_StateAndAreaEmployment")
OUTPUT_FILE = DATA_DIR / "all_data_combined.xlsx"

if __name__ == "__main__":
 
    pathlist = DATA_DIR.glob('SeriesReport-*.xlsx')
    all_data_df = pandas.DataFrame()
    for path in pathlist:
        print("Reading {}".format(path))

        # read the metadata
        metadata = {}
        # ignore UserWarning: Workbook contains no default style, apply openpyxl's default
        with warnings.catch_warnings(record=True) as w:
             warnings.simplefilter("always")
             workbook = openpyxl.load_workbook(path)

        worksheet = workbook.active
        for row in range(4,12):
            key = worksheet["A{}".format(row)].value
            value = worksheet["B{}".format(row)].value
            if value == None:
                value = key  
                key = "Adjustment"
            else:
                key = key[:-1] # remove trailing : from key
            metadata[key] = value
        print ("  Area: {}".format(metadata['Area']))
        print ("  Adjustment: {}".format(metadata['Adjustment']))
        
        # read the data
        sae_data_df = None
        # ignore UserWarning: Workbook contains no default style, apply openpyxl's default
        with warnings.catch_warnings(record=True) as w:
             warnings.simplefilter("always")
             sae_data_df = pandas.read_excel(path, header=12)
        # convert to long
        sae_data_df = sae_data_df.melt(
            id_vars=['Year'], 
            value_vars=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
            var_name = 'Month',
            value_name = metadata['Data Type'])
        
        # add metadata
        for key in metadata.keys():
            if key == 'Data Type': continue
            sae_data_df[key] = metadata[key]
        # print(sae_data_df)

        # add to full set
        all_data_df = pandas.concat([all_data_df, sae_data_df])

    # save to combined file
    all_data_df.to_excel(OUTPUT_FILE, sheet_name="BLS Data Series", index=False)
    print("Wrote {}".format(OUTPUT_FILE))