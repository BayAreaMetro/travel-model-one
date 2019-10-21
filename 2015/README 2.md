### basis.py

`scripts/basis.py` is a script used to operate on this data.  There are several modes of operation (use the --mode command line option), analagous to baus.py in the bayarea_urbansim directory.  The modes include:

* `merge_gp_data` which merges the general plan data from each jurisdiction into a single file (edit the code to pick which output format you'd prefer)
* `diagnose_merge` which is used to find rows in zoning_lookup.csv which are currently assigned to parcels, which do not occur in the general plan shapefiles.  There are currently about 190 rows which are missing which are written to [missing_zoning_ids.csv](https://github.com/oaklandanalytics/badata/blob/master/missing_zoning_ids.csv) - this csv includes an attribute "Parcel Count" which is the number of parcels which have that id.  These missing shapes are an issue because these zones will not be assigned in future merges of the parcels and general plan shapes.
