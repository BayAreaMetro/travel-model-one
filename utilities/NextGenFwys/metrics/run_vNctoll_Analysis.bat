setlocal enabledelayedexpansion
REM see info about "setlocal enabledelayedexpansion" and setting variables inside a loop here: 
REM https://stackoverflow.com/questions/13805187/how-to-set-a-variable-inside-a-loop-for-f


IF %USERNAME%==ftsang (
  set R_HOME=C:\Program Files\R\R-4.1.2\bin
)

IF %USERNAME%==llin (
  set R_HOME=C:\Program Files\R\R-4.2.2rc\bin
)


REM for NGF Round 1, the TARGET_DIR are: 
for /d %%f in (

    //MODEL2-C/Model2C-Share/Projects/2035_TM152_NGF_NP10_Path4_02       
    //MODEL3-C/Model3C-Share/Projects/2035_TM152_NGF_NP10_Path3a_02  
    //MODEL3-D/Model3D-Share/Projects/2035_TM152_NGF_NP10_Path3b_02 
    //MODEL3-A/Model3A-Share/Projects/2035_TM152_NGF_NP10_Path1a_02    
    //MODEL3-B/Model3B-Share/Projects/2035_TM152_NGF_NP10_Path1b_02      
    //MODEL2-D/Model2D-Share/Projects/2035_TM152_NGF_NP10_Path2a_02_10pc
    //MODEL3-D/Model3D-Share/Projects/2035_TM152_NGF_NP10_Path2b_02_10pc

)    do    (

REM set target directory and run the script
set TARGET_DIR=%%f
"%R_HOME%\Rscript.exe" X:\travel-model-one-master\utilities\NextGenFwys\metrics\Analyse_vtoll_distribution.R

REM copy the key outputs to L:
for %%I in ("!TARGET_DIR!") do set "run_id=%%~nxI"
echo !TARGET_DIR!
echo !run_id!

copy "!TARGET_DIR!\updated_output\hhld_vNctoll_stats.csv" "L:\Application\Model_One\NextGenFwys\across_runs_union\hhld_vNctoll_stats_!run_id!.csv"

)




