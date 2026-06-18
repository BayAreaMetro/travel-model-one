; Convert the loaded highway network to shapefiles (links and nodes),
; so the network is readable in Python via GeoPandas.
;
; TEMPLATE — fill in the real .net path once you have a model run to test against
; (this example uses avgLOADEV.net, the loaded average network RunIteration.bat
; produces; there may be several .net files — pick the one you actually want).
; Run with cwd set to the scenario root, so paths below are relative to it.
;
; CRS note: shapefiles exported this way usually have no coordinate system
; attached. Assign one yourself in Python, e.g. gpd.read_file(...).set_crs(...).

RUN PGM=NETWORK

FILEI NETI="hwy\avgLOADEV.net"

FILEO LINKO="data\interim\network\links.shp",
      NODEO="data\interim\network\nodes.shp"

ENDRUN
