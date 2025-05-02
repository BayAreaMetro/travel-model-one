
USAGE="""
Assigns TAZ1454 tazs to cities and outputs file, TAZ1454_city.csv with columns
 TAZ1454,city,area,overlap_area,overlap_pct

"""
import pathlib
import pandas as pd
import geopandas as gpd

if __name__ == '__main__':
    TAZ_FILE = pathlib.Path(__file__) / ".." / ".." / "geographies" / "bayarea_rtaz1454_rev1_WGS84.shp"
    # this is very old but it was used for the links
    CITIES_FILE = pathlib.Path("M:\Development\Travel Model One\Version 05\Adding City to Master Network\Cityshapes\PBA_Cities_NAD_1983_UTM_Zone_10N.shp")
    
    # read cities file
    cities_gdf = gpd.read_file(CITIES_FILE)
    cities_gdf = cities_gdf[['name','geometry']]
    print(cities_gdf.dtypes)
    print(cities_gdf.crs)
    cities_gdf['city_geom'] = cities_gdf.geometry # make a copy
    print(f"cities_gdf:\n{cities_gdf}")
    print(cities_gdf.crs)

    taz_gdf = gpd.read_file(TAZ_FILE)
    print(f"Read taz_gdf from {TAZ_FILE.resolve()}")
    taz_gdf = taz_gdf[['TAZ1454','geometry']]
    # project to same CRS as taz_gdf
    taz_gdf = taz_gdf.to_crs(cities_gdf.crs)
    # calculate area in CRS units - meters
    taz_gdf['area'] = taz_gdf.area
    print(f"taz_gdf:\n{taz_gdf}")
    print(taz_gdf.dtypes)
    print(taz_gdf.crs)

    taz_with_cities_gdf = gpd.sjoin(
        left_df=taz_gdf,
        right_df=cities_gdf,
        how='inner',
        predicate='intersects')
    # calculate overlap area
    taz_with_cities_gdf["overlap_area"] = taz_with_cities_gdf.apply(lambda x: x["geometry"].intersection(x["city_geom"]).area if x["city_geom"] is not None else 0, axis=1)
    taz_with_cities_gdf["overlap_pct"] = taz_with_cities_gdf.overlap_area / taz_with_cities_gdf.area

    # drop this column since writing with two geometry columns is not allowed
    taz_with_cities_gdf.drop(columns=['city_geom'], inplace=True)

    # sort so biggest overlap_pct is first
    taz_with_cities_gdf.sort_values(by=['TAZ1454','overlap_pct'], ascending=[True,False], inplace=True)
    taz_with_cities_gdf.reset_index(inplace=True)
    print(f"taz_with_cities_gdf:\n{taz_with_cities_gdf}")
    # print debug shapefile
    # taz_with_cities_gdf.to_file("taz_with_cities.shp")

    # drop duplicates, choosing first for each taz, which has highest overlap pct
    taz_with_cities_df = pd.DataFrame(taz_with_cities_gdf)
    taz_with_cities_df = taz_with_cities_df[['TAZ1454','name','area','overlap_area','overlap_pct']]
    taz_with_cities_df.rename(columns={'name':'city'}, inplace=True)
    taz_with_cities_df.drop_duplicates(subset='TAZ1454', keep='first', inplace=True)
    print(taz_with_cities_df)
    taz_with_cities_df.to_csv("TAZ1454_city.csv", index=False)

