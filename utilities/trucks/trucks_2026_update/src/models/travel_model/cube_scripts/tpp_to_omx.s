; Convert truck OD matrices from CUBE's .tpp format to .omx, so they're
; readable in Python. One CONVERTMAT block per .tpp file.
;
; TEMPLATE — fill in the real .tpp filenames/paths your model run produces
; (check hwy\ or wherever RunIteration.bat writes outputs), one CONVERTMAT block
; per file (no loop construct — list them all out). Run with cwd set to the
; scenario root, so the paths below are relative to it.

;RUN PGM=MATRIX

CONVERTMAT FROM='nonres/TripsTrkPMx.tpp' TO='nonres/TripsTrkPMx.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='nonres/TripsTrkAMx.tpp' TO='nonres/TripsTrkAMx.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='nonres/TripsTrkMDx.tpp' TO='nonres/TripsTrkMDx.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='nonres/TripsTrkEVx.tpp' TO='nonres/TripsTrkEVx.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='nonres/TripsTrkEAx.tpp' TO='nonres/TripsTrkEAx.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='nonres/ixDailyx4.tpp' TO='nonres/ixDailyx4.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='nonres/ixDailyx4_truck.tpp' TO='nonres/ixDailyx4_truck.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='nonres/DailyTruckTrips.tpp' TO='nonres/DailyTruckTrips.omx' FORMAT=OMX COMPRESSION=4

;ENDRUN


