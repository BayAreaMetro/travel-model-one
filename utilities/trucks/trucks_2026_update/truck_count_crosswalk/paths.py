"""Every path this analysis reads or writes, in one place.

Raw inputs live under the truck project's Box share in ``data/external``;
everything derived lands in ``data/interim``.  Scripts import from here and
offer ``--`` overrides for one-off runs against other locations.

The network is the loaded base-scenario network the TM1.7 truck scenarios are
built from: ``extractor/avgload5period.net`` out of ``2023_TM161_IPA_35.zip``
(Box, ``Development/Travel Model 1.7/``).  TM1.7 changes truck demand, not the
network, so one crosswalk serves every scenario.
"""

from pathlib import Path

DATA = Path(
    r"E:\Box\Modeling and Surveys\Development\Travel Model Two Conversion"
    r"\TrucksAirports\Trucks\data"
)

# Raw Caltrans publications: one truck-AADT workbook per year, plus the point
# layer that georeferences the count locations.
RAW_COUNTS = DATA / "external" / "caltrans" / "counts" / "truck_counts"
LOCATIONS_GEOJSON = RAW_COUNTS / "Truck_Volumes_AADT.geojson"

# The model network, beside the project's own mtc_links.shp export of it.
NETWORK = DATA / "interim" / "cube_io" / "mtc_net" / "avgload5period.net"

# Everything this analysis derives, named for its source: the published truck
# AADT book (as opposed to the hourly class-count stations beside it).
OUT = DATA / "interim" / "observed_data" / "caltrans" / "truck_aadt_book"
COUNTS_CSV = OUT / "caltrans_truck_aadt_2013_2024.csv"
