This project is the same as PPA project 6100_TransitFare_Integration.
The TransitSkims.job in this directory has been copied from L:\RTP2021_PPA\Projects\6100_TransitFare_Integration\travel-model-overrides

For setupmodel, we can use this line:
copy /Y "\\tsclient\L\RTP2021_PPA\Projects\6100_TransitFare_Integration\travel-model-overrides\TransitSkims.job"     CTRAMP\scripts\skims

or 

copy /Y "%BP_OVERRIDE_DIR%\TransitSkims.job"     CTRAMP\scripts\skims
