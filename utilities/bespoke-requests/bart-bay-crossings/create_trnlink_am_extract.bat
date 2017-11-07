set INPUT_DIR=E:\Projects\2035_06_694\trn
set OUTPUT_DIR=M:\Application\Model One\RTP2017\Scenarios\2035_06_694\OUTPUT\trn
set CODE_DIR=C:\Users\lzorn\Documents\travel-model-one-v05\model-files\scripts\core_summaries

FOR %%J in (loc lrf exp hvy com) DO (
  rem walk -> transit -> walk
  python "%CODE_DIR%\RdataToTableauExtract.py" --output trnlink_am.tde --join "%CODE_DIR%\reference-transit-modes.csv" --append "%INPUT_DIR%" "%OUTPUT_DIR%" trnlinkam_wlk_%%J_wlk.dbf
  rem drive -> transit -> walk
  python "%CODE_DIR%\RdataToTableauExtract.py" --output trnlink_am.tde --join "%CODE_DIR%\reference-transit-modes.csv" --append "%INPUT_DIR%" "%OUTPUT_DIR%" trnlinkam_drv_%%J_wlk.dbf      
  rem walk -> transit -> drive
  python "%CODE_DIR%\RdataToTableauExtract.py" --output trnlink_am.tde --join "%CODE_DIR%\reference-transit-modes.csv" --append "%INPUT_DIR%" "%OUTPUT_DIR%" trnlinkam_wlk_%%J_drv.dbf
)
