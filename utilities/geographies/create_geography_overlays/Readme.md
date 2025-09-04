[prepare_Geographies_for_overlay_crosswalk.py](prepare_Geographies_for_overlay_crosswalk.py)
* Prepares geographies data (e.g. Growth Geographies, Transit-Rich Areas) for the overlay crosswalk script, e.g. assigning unique ID, dissolving/intersecting/unioning raw geographies into the desired categories. 

[TAZ_otherGeographies_overlay_crosswalk.py](TAZ_Census_otherGeographies_overlay_crosswalk.py)
* Creates crosswalk between two geographies (e.g. betwen TAZ1454 and Growth Geographies) based on spatial overlay with *largest intersection* rule.

[build_TAZ1454_crosswalks_RTP2025.ipynb](build_TAZ1454_crosswalks_RTP2025.ipynb)
* Documents the creation of the various TAZ-related crosswalks used in PBA50+, mainly as modeling input. It calls `prepare_Geographies_for_overlay_crosswalk.py` and `TAZ_otherGeographies_overlay_crosswalk.py`.

[correspond_link_to_TAZ.py](correspond_link_to_TAZ.py)
* Joins network link shapefile to TAZ (or any other) shapefile and determines correspondence between link => shape, portion of link.
  Note that some links may span more than one shape; in this case, the link will be included multiple times, one for each shape. Therefore, (A, B, TAZ1454) is unique, but (A, B) is not.
