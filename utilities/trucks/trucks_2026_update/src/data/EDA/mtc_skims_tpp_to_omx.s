* if not exist "data\interim\cube_io\mtc_skims" mkdir "data\interim\cube_io\mtc_skims"

CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\skims\COM_HWYSKIMAM.tpp' TO='data\interim\cube_io\mtc_skims\COM_HWYSKIMAM.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\skims\COM_HWYSKIMEA.tpp' TO='data\interim\cube_io\mtc_skims\COM_HWYSKIMEA.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\skims\COM_HWYSKIMEV.tpp' TO='data\interim\cube_io\mtc_skims\COM_HWYSKIMEV.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\skims\COM_HWYSKIMMD.tpp' TO='data\interim\cube_io\mtc_skims\COM_HWYSKIMMD.omx' FORMAT=OMX COMPRESSION=4
CONVERTMAT FROM='data\external\mtc\2023_TM161_IPA_35\skims\COM_HWYSKIMPM.tpp' TO='data\interim\cube_io\mtc_skims\COM_HWYSKIMPM.omx' FORMAT=OMX COMPRESSION=4