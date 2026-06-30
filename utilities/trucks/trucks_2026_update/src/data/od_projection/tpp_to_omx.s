CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkPMx.tpp' TO='data\interim\cube_io\mtc_truck_od_trips\TripsTrkPMx.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkAMx.tpp' TO='data\interim\cube_io\mtc_truck_od_trips\TripsTrkAMx.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkMDx.tpp' TO='data\interim\cube_io\mtc_truck_od_trips\TripsTrkMDx.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkEVx.tpp' TO='data\interim\cube_io\mtc_truck_od_trips\TripsTrkEVx.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkEAx.tpp' TO='data\interim\cube_io\mtc_truck_od_trips\TripsTrkEAx.omx' FORMAT=OMX COMPRESSION=4

; Create a Cube-compatible copy of OMX files to modify safely without altering the originals because they might be use for other calculations. 
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkPMx.tpp' TO='data\interim\matrix_projection\sw_od_trips_with_mtc_format\TripsTrkPMx.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkAMx.tpp' TO='data\interim\matrix_projection\sw_od_trips_with_mtc_format\TripsTrkAMx.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkMDx.tpp' TO='data\interim\matrix_projection\sw_od_trips_with_mtc_format\TripsTrkMDx.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkEVx.tpp' TO='data\interim\matrix_projection\sw_od_trips_with_mtc_format\TripsTrkEVx.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkEAx.tpp' TO='data\interim\matrix_projection\sw_od_trips_with_mtc_format\TripsTrkEAx.omx' FORMAT=OMX COMPRESSION=4

; CSF2TDM Truck OD matrices
CONVERTMAT FROM='data\external\caltrans\Year2020\FFM\Trips\TRIPS_FFM_2020.mat' TO='data\interim\cube_io\statewide_od_matrices\TRIPS_FFM_2020.omx' FORMAT=OMX COMPRESSION=4