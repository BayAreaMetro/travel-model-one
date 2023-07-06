# U.S. Department of Labor
# Bureau of Labor Statistics 
# Quarterly Census of Employment and Wages
# July 2014
#  
# QCEW Open Data Access for Python 3.x
#  
# This version was written using Python 3.3 and should work with other "3.x"
# versions. However, some modification may be needed. There is a separate 
# example file for "2.x" versions Python. 
#
#
# Submit questions at: http://www.bls.gov/cgi-bin/forms/cew?/cew/home.htm 
#
# *******************************************************************************


import urllib.request
import urllib

# *******************************************************************************
# qcewCreateDataRows : This function takes a raw csv string and splits it into
# a two-dimensional array containing the data and the header row of the csv file
# a try/except block is used to handle for both binary and char encoding
def qcewCreateDataRows(csv):
    dataRows = []
    try: dataLines = csv.decode().split('\r\n')
    except er: dataLines = csv.split('\r\n');
    for row in dataLines:
        dataRows.append(row.split(','))
    return dataRows
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



Michigan_Data = qcewGetAreaData("2015","1","26000")
Auto_Manufacturing = qcewGetIndustryData("2015","1","3361")
SizeData = qcewGetSizeData("2015","6")

# prints the industry_code in row 5.
# remember row zero contains field names
print(Michigan_Data[5][2])


# prints the area_fips in row 1.
# remember row zero contains field names
print(Auto_Manufacturing[1][0])


# prints the own_code in row 1.
# remember row zero contains field names
print(SizeData[1][1])
