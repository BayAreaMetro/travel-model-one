::
:: This batch script is just for convenience, if the cobra metrics are calculated outside
:: of the normal run environment and you need to copy over the required inputs.
:: If so, set the following environment variables and run.
:: 
:: ITER=the iteration corresponding to the output for which we'll calculate metrics.
:: e.g. 
::   set ITER=1
:: RUN_DIR=the model run directory containing the files (skims, trip files, hwy assignment).
:: e.g.
::   set RUN_DIR=B:\Projects\2040_03_116.archived
::

:: copy required inputs
if not exist main (mkdir main)
if not exist main\indivTripData_%ITER%.csv (copy %RUN_DIR%\main\indivTripData_%ITER%.csv main)
if not exist main\jointTripData_%ITER%.csv (copy %RUN_DIR%\main\jointTripData_%ITER%.csv main)
if not exist main\householdData_%ITER%.csv (copy %RUN_DIR%\main\householdData_%ITER%.csv main)

if not exist hwy\iter%ITER% (mkdir hwy\iter%ITER%)
if not exist hwy\iter%ITER%\avgload5period.net (copy %RUN_DIR%\hwy\iter%ITER%\avgload5period.net hwy\iter%ITER%)

if not exist CTRAMP\scripts\block (mkdir CTRAMP\scripts\block)
if not exist CTRAMP\scripts\block\hwyParam.block (copy %RUN_DIR%\CTRAMP\scripts\block\hwyParam.block CTRAMP\scripts\block)

if not exist nonres (mkdir nonres)
if not exist trn (mkdir trn)
if not exist skims (mkdir skims)
for %%H in (ea am md pm ev) DO (
  for %%J in (loc lrf exp hvy com) DO (
    if not exist skims\trnskm%%H_wlk_%%J_wlk.tpp (copy %RUN_DIR%\skims\trnskm%%H_wlk_%%J_wlk.tpp skims)
    if not exist skims\trnskm%%H_drv_%%J_wlk.tpp (copy %RUN_DIR%\skims\trnskm%%H_drv_%%J_wlk.tpp skims)
    if not exist skims\trnskm%%H_wlk_%%J_drv.tpp (copy %RUN_DIR%\skims\trnskm%%H_wlk_%%J_drv.tpp skims)

    if not exist trn\trnlink%%H_wlk_%%J_wlk.dbf (copy %RUN_DIR%\trn\trnlink%%H_wlk_%%J_wlk.dbf trn)
    if not exist trn\trnlink%%H_drv_%%J_wlk.dbf (copy %RUN_DIR%\trn\trnlink%%H_drv_%%J_wlk.dbf trn)
    if not exist trn\trnlink%%H_wlk_%%J_drv.dbf (copy %RUN_DIR%\trn\trnlink%%H_wlk_%%J_drv.dbf trn)
  )
  if not exist nonres\tripstrk%%H.tpp   (copy %RUN_DIR%\nonres\tripstrk%%H.tpp nonres)
  if not exist skims\HWYSKM%%H.tpp      (copy %RUN_DIR%\skims\HWYSKM%%H.tpp skims)
  if not exist skims\COM_HWYSKIM%%H.tpp (copy %RUN_DIR%\skims\COM_HWYSKIM%%H.tpp skims)
)

if not exist skims\nonmotskm.tpp (copy %RUN_DIR%\skims\nonmotskm.tpp skims)