"""
Python script to generate average shadow pricing files for use in PPA 2050.
 
author: william.wang@rsginc.com, 29 February 2024
"""
 
import pandas as pd
 
def average_shadowpricing(files, output_path=None):
 
    # read in each shadow price file
    dfs = []
    for f in files:
        print(f"reading shadow price file from {f}")
        df = pd.read_csv(f, index_col=['alt', 'zone', 'subzone'])
        dfs.append(df)
   
    # initialize the average dataframe as first file
    average_df = dfs[0].copy()
 
    # check dfs are as expected
    for df in dfs:
        assert (df.columns == average_df.columns).all(), f"Columns are not the same! left: {average_df.columns}, right: {df.columns}"
        pd.testing.assert_index_equal(average_df.index, df.index)
 
    # sum each column and divide by the number of files
    for col in df.columns:
        for df in dfs[1:]:
            average_df[col] += df[col]
        average_df[col] /= len(files)
 
    # write to output path if provided
    if output_path:
        print(f"writing averaged files to {output_path}")
        average_df.to_csv(output_path, index=True)
   
    return average_df
 
 
if __name__ == "__main__":
    files = [
        r"Z:\RTP2025_PPA\Projects\2050_TM151_PPA_BF_18\run1\OUTPUT\main\ShadowPricing_7_.csv",
        r"Z:\RTP2025_PPA\Projects\2050_TM151_PPA_BF_18\run2\OUTPUT\main\ShadowPricing_7.csv",
        r"Z:\RTP2025_PPA\Projects\2050_TM151_PPA_BF_18\run3\OUTPUT\main\ShadowPricing_7.csv",
    ]
    output_path = r"Z:\RTP2025_PPA\Projects\2050_TM151_PPA_BF_18\INPUT\ShadowPricing_7.csv"
    averaged_df = average_shadowpricing(files, output_path)
 