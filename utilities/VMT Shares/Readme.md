VMT Shares
==========

The [core summaries][https://github.com/MetropolitanTransportationCommission/travel-model-one/tree/master/model-files/scripts/core_summaries] scripts now output some files relavant for VMT share analysis.

The *aspnet* subdirectory contains an ASP.NET prototype for summarizing that data for arbitrary TAZ sets.  This analysis requires two different tables in a SQL Server database per model run.  In the following, `YYYY_MV_MVV` is the model run name.


### Persons Table, `persons_YYYY_MV_MVV`

The output of `AutoTripsVMT_personsHomeWork.csv` will be imported into this table.  Columns are:

* COUNTY, tinyint
* county_name, varchar(25)
* taz, smallint
* WorkLocation, smallint
* freq, int

###  VMT Table, `vmt_YYYY_MV_MVV`

The output of `AutoTripsVMT_perOrigDestHomeWork.csv` will be imported into this table.  Columns are:

* orig_taz, smallint
* dest_taz, smallint
* taz, smallint
* WorkLocation, smallint
* vmt, real
* vmt_indiv, real
* vmt_join, real
* trips, int

## Importing Data

After creating the data files by running the *core_summaries* scripts, do the following to import to the SQL Server.
1. Run "SQL Server Import and Export Wizard (64-bit)" (standalone program)
2. Choose Source: Flat File Source
3. Select csv, no mods to columns but delete unneeded columns
4. Choose Destination: Microsoft OLE DB Provider for SQL Server
5. Enter server name: (we're using 54.201.106.213)
6. Use SQL Server Authentication: (user, pass)
7. Database: gis (refresh after entering user, pass)
8. Name destination table, e.g. `[vmt_2010_03_YYY]`
9. Choose _Edit Mappings_ and set destination types to be as above, with none as Nullable. Make sure the Destination column names are not in quotes.