@echo on

:: Created by lmz on 1/26/2017
:: Applies core summaries update which just adds a few columns and another file

:: The location of R and R libraries
set R_HOME=C:\Program Files\R\R-3.2.3
set R_LIB=C:/Users/mtcpb/Documents/R/win-library/3.2

set ITER=3
set SAMPLESHARE=0.50

set DIRS=2020_06_690 2020_06_695 2035_06_690 2040_06_691 2040_06_695
:: 2040_06_694 is done; used for testing

for %%D in (%DIRS%) do (
  echo Running core summaries for [%%D]
  cd %%D
  move core_summaries core_summaries_orig
  move updated_output updated_output_orig

  set TARGET_DIR=M:\Projects\%%D
  "%R_HOME%\bin\x64\Rscript.exe" --vanilla ..\CoreSummaries.R

  rem back up the old files
  move core_summaries_orig\AutoTripsVMT_perOrigDestHomeWork.csv   core_summaries_orig\AutoTripsVMT_perOrigDestHomeWork_bak.csv
  move core_summaries_orig\AutoTripsVMT_perOrigDestHomeWork.rdata core_summaries_orig\AutoTripsVMT_perOrigDestHomeWork_bak.rdata
  move core_summaries_orig\VehicleMilesTraveled.csv               core_summaries_orig\VehicleMilesTraveled_bak.csv
  move core_summaries_orig\VehicleMilesTraveled.rdata             core_summaries_orig\VehicleMilesTraveled_bak.rdata

  rem copy the updated files
  move core_summaries\AutoTripsVMT_perOrigDestHomeWork.csv   core_summaries_orig\
  move core_summaries\AutoTripsVMT_perOrigDestHomeWork.rdata core_summaries_orig\
  move core_summaries\VehicleMilesTraveled.csv               core_summaries_orig\
  move core_summaries\VehicleMilesTraveled.rdata             core_summaries_orig\

  rem copy the new files
  move core_summaries\VehicleMilesTraveled_households.csv    core_summaries_orig\
  move core_summaries\VehicleMilesTraveled_households.rdata  core_summaries_orig\

  rem delete the new and restore the orig
  rmdir /s /q core_summaries
  move core_summaries_orig core_summaries

  cd ..
)