USAGE="""

  Fetches U.S. Department of Labor Bureau of Labor Statistics (BLS) 
  Quarterly Census of Employment and Wages (QCEW) data for Bay Area counties
  by year or year+quarter

"""

import argparse, io, urllib, sys
import urllib.request
import pandas

BAY_AREA_COUNTY_FIPS = {
    "06001": "Alameda",
    "06013": "Contra Costa",
    "06041": "Marin",
    "06055": "Napa",
    "06075": "San Francisco",
    "06081": "San Mateo",
    "06085": "Santa Clara",
    "06095": "Solano",
    "06097": "Sonoma"
}

# *******************************************************************************
# qcewCreateDataRows : This function takes a raw csv bytes string and converts it
# to a pandas.DataFrame.
def qcewCreateDataRows(csv):
    dataframe = pandas.read_csv(io.BytesIO(csv))    
    return dataframe
# *******************************************************************************


# *******************************************************************************
# qcewGetAreaData : This function takes a year, quarter, and area argument and
# returns an array containing the associated area data. Use 'a' for annual
# averages. 
# For all area codes and titles see:
# http://www.bls.gov/cew/doc/titles/area/area_titles.htm
#
def qcewGetAreaData(year,qtr,area):
    urlPath = "http://data.bls.gov/cew/data/api/[YEAR]/[QTR]/area/[AREA].csv"
    urlPath = urlPath.replace("[YEAR]",year)
    urlPath = urlPath.replace("[QTR]",qtr.lower())
    urlPath = urlPath.replace("[AREA]",area.upper())
    httpStream = urllib.request.urlopen(urlPath)
    csv = httpStream.read()
    httpStream.close()
    return qcewCreateDataRows(csv)
# *******************************************************************************




# *******************************************************************************
# qcewGetIndustryData : This function takes a year, quarter, and industry code
# and returns an array containing the associated industry data. Use 'a' for 
# annual averages. Some industry codes contain hyphens. The CSV files use
# underscores instead of hyphens. So 31-33 becomes 31_33. 
# For all industry codes and titles see:
# http://www.bls.gov/cew/doc/titles/industry/industry_titles.htm
#
def qcewGetIndustryData(year,qtr,industry):
    urlPath = "http://data.bls.gov/cew/data/api/[YEAR]/[QTR]/industry/[IND].csv"
    urlPath = urlPath.replace("[YEAR]",year)
    urlPath = urlPath.replace("[QTR]",qtr.lower())
    urlPath = urlPath.replace("[IND]",industry)
    httpStream = urllib.request.urlopen(urlPath)
    csv = httpStream.read()
    httpStream.close()
    return qcewCreateDataRows(csv)
# *******************************************************************************




# *******************************************************************************
# qcewGetSizeData : This function takes a year and establishment size class code
# and returns an array containing the associated size data. Size data
# is only available for the first quarter of each year.
# For all establishment size classes and titles see:
# http://www.bls.gov/cew/doc/titles/size/size_titles.htm
#
def qcewGetSizeData(year,size):
    urlPath = "http://data.bls.gov/cew/data/api/[YEAR]/1/size/[SIZE].csv"
    urlPath = urlPath.replace("[YEAR]",year)
    urlPath = urlPath.replace("[SIZE]",size)
    httpStream = urllib.request.urlopen(urlPath)
    csv = httpStream.read()
    httpStream.close()
    return qcewCreateDataRows(csv)
# *******************************************************************************

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("year", help='Year of data')
    parser.add_argument("quarter", choices=['A','1','2','3','4'])
    args = parser.parse_args()

    output_file = "qcew_BayArea_{}_{}.csv".format(
        args.year,
        "annual" if args.quarter=="A" else "Q{}".format(args.quarter)
    )
    print("output_file: {}".format(output_file))
    
    bay_area_df = pandas.DataFrame()
    for fips in BAY_AREA_COUNTY_FIPS.keys():
        county_df = qcewGetAreaData(args.year,args.quarter,fips)
        county_df['county'] = BAY_AREA_COUNTY_FIPS[fips]
        bay_area_df = pandas.concat([bay_area_df, county_df])
        print("Fetched data for {}".format(BAY_AREA_COUNTY_FIPS[fips]))
    bay_area_df.to_csv(output_file, index=False)
    print("Wrote {} lines to {}".format(len(bay_area_df), output_file))
