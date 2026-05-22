CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkPMx.tpp' TO='data\interim\cube_io\from_cube\mtc_truck_od_trips\TripsTrkPMx.omx' FORMAT=OMX COMPRESSION=0
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkAMx.tpp' TO='data\interim\cube_io\from_cube\mtc_truck_od_trips\TripsTrkAMx.omx' FORMAT=OMX COMPRESSION=0
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkMDx.tpp' TO='data\interim\cube_io\from_cube\mtc_truck_od_trips\TripsTrkMDx.omx' FORMAT=OMX COMPRESSION=0
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkEVx.tpp' TO='data\interim\cube_io\from_cube\mtc_truck_od_trips\TripsTrkEVx.omx' FORMAT=OMX COMPRESSION=0
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkEAx.tpp' TO='data\interim\cube_io\from_cube\mtc_truck_od_trips\TripsTrkEAx.omx' FORMAT=OMX COMPRESSION=0

; Create a Cube-compatible copy of OMX files to modify safely without altering the originals because they might be use for other calculations. 
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkPMx.tpp' TO='data\interim\matrix_projection\outputs\od_matrices_for_tm\TripsTrkPMx.omx' FORMAT=OMX COMPRESSION=0
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkAMx.tpp' TO='data\interim\matrix_projection\outputs\od_matrices_for_tm\TripsTrkAMx.omx' FORMAT=OMX COMPRESSION=0
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkMDx.tpp' TO='data\interim\matrix_projection\outputs\od_matrices_for_tm\TripsTrkMDx.omx' FORMAT=OMX COMPRESSION=0
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkEVx.tpp' TO='data\interim\matrix_projection\outputs\od_matrices_for_tm\TripsTrkEVx.omx' FORMAT=OMX COMPRESSION=0
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\nonres\TripsTrkEAx.tpp' TO='data\interim\matrix_projection\outputs\od_matrices_for_tm\TripsTrkEAx.omx' FORMAT=OMX COMPRESSION=0