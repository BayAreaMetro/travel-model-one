::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: ExtractKeyFiles.bat
::
:: MS-DOS batch file to extract key model files from various model run directories
:: for quick exporting for data summary.
::
:: lmz - Create version for PBAU (Plan Bay Area Update)
::
:: This just pulls output into extractor\
::
:: See also CopyFilesToM.bat, which is meant to run afterwards
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo STARTED EXTRACTOR RUN  %DATE% %TIME% >> logs\feedback.rpt

:: Create the needed directories
mkdir extractor

:: Assume this is set already
:: set ITER=3

:: Highway assignment results
copy hwy\iter%ITER%\avgload5period.net            extractor\avgload5period.net
copy hwy\iter%ITER%\avgload5period.csv            extractor\avgload5period.csv
copy hwy\iter%ITER%\avgload5period_vehclasses.csv extractor\avgload5period_vehclasses.csv

:: Transit assignment results
mkdir extractor\trn
copy trn\TransitAssignment.iter3\trnline*.csv    extractor\trn
copy trn\trnlink*.dbf                            extractor\trn
copy trn\trnlink.csv                             extractor\trn
copy trn\trnline.csv                             extractor\trn
copy trn\quickboards.xls                         extractor\trn

:: Demand results
copy main\householdData_%ITER%.csv extractor\main\householdData_%ITER%.csv
copy main\personData_%ITER%.csv    extractor\main\personData_%ITER%.csv
copy main\indivTripData_%ITER%.csv extractor\main\indivTripData_%ITER%.csv
copy main\indivTourData_%ITER%.csv extractor\main\indivTourData_%ITER%.csv
copy main\jointTripData_%ITER%.csv extractor\main\jointTripData_%ITER%.csv
copy main\jointTourData_%ITER%.csv extractor\main\jointTourData_%ITER%.csv
copy main\wsLocResults_%ITER%.csv  extractor\main\wsLocResults_%ITER%.csv

:: Report results
copy logs\HwySkims.debug  extractor\HwySkims.debug
copy logs\feedback.rpt    extractor\feedback.rpt
copy logs\SpeedErrors.log extractor\SpeedErrors.log

:: Skim databases
:: These are huge - don't do this until final runs
:: mkdir extractor\skimDB
:: copy database\*.csv extractor\skimDB\*.csv

:: Trip tables
mkdir extractor\main
copy main\tripsEA.tpp extractor\main
copy main\tripsAM.tpp extractor\main
copy main\tripsMD.tpp extractor\main
copy main\tripsPM.tpp extractor\main
copy main\tripsEV.tpp extractor\main
copy main\ShadowPricing_7.csv extractor\main

mkdir extractor\nonres
copy nonres\ixDaily2015.tpp       extractor\nonres
copy nonres\ixDailyx4.tpp         extractor\nonres
copy nonres\tripsIX*.tpp          extractor\nonres
copy nonres\tripsTrk*.tpp         extractor\nonres

:: take the whole emfac foler
c:\windows\system32\Robocopy.exe /E emfac extractor\emfac

:: copy skims\hwyskmEA.tpp extractor\emfac\hwyskmEA.tpp
:: copy skims\hwyskmAM.tpp extractor\emfac\hwyskmAM.tpp
:: copy skims\hwyskmMD.tpp extractor\emfac\hwyskmMD.tpp
:: copy skims\hwyskmPM.tpp extractor\emfac\hwyskmPM.tpp
:: copy skims\hwyskmEV.tpp extractor\emfac\hwyskmEV.tpp

:: copy skims\com_hwyskimEA.tpp extractor\emfac\com_hwyskimEA.tpp
:: copy skims\com_hwyskimAM.tpp extractor\emfac\com_hwyskimAM.tpp
:: copy skims\com_hwyskimMD.tpp extractor\emfac\com_hwyskimMD.tpp
:: copy skims\com_hwyskimPM.tpp extractor\emfac\com_hwyskimPM.tpp
:: copy skims\com_hwyskimEV.tpp extractor\emfac\com_hwyskimEV.tpp

:: copy nonres\tripsTrkEA.tpp extractor\emfac\tripsTrkEA.tpp
:: copy nonres\tripsTrkAM.tpp extractor\emfac\tripsTrkAM.tpp
:: copy nonres\tripsTrkMD.tpp extractor\emfac\tripsTrkMD.tpp
:: copy nonres\tripsTrkPM.tpp extractor\emfac\tripsTrkPM.tpp
:: copy nonres\tripsTrkEV.tpp extractor\emfac\tripsTrkEV.tpp

:: Save the control file
copy CTRAMP\runtime\mtcTourBased.properties extractor\mtcTourBased.properties
copy CTRAMP\runtime\mtcTourBased.properties extractor\logsums.properties

:: Accessibility files - model results
mkdir extractor\logsums
copy logsums\householdData_%ITER%.csv                extractor\logsums
copy logsums\personData_%ITER%.csv                   extractor\logsums
copy logsums\indivTripData_%ITER%.csv                extractor\logsums
copy logsums\indivTourData_%ITER%.csv                extractor\logsums
copy logsums\wsLocResults_%ITER%.csv                 extractor\logsums
:: summaries from logsumJoiner
copy logsums\shopDCLogsum.csv                        extractor\logsums
copy logsums\tour_shopDCLogsum.csv                   extractor\logsums
copy logsums\workDCLogsum.csv                        extractor\logsums
copy logsums\person_workDCLogsum.csv                 extractor\logsums
copy logsums\mandatoryAccessibilities.csv            extractor\logsums
copy logsums\nonMandatoryAccessibilities.csv         extractor\logsums
:: for BAUS
copy logsums\subzone_logsums_for_BAUS.csv            extractor\logsums
copy logsums\taz_logsums_for_BAUS.csv                extractor\logsums

:: Core summaries
mkdir extractor\core_summaries
copy core_summaries\*.*                              extractor\core_summaries
mkdir extractor\updated_output
copy updated_output\*.*                              extractor\updated_output

:: metrics
mkdir extractor\metrics
copy metrics extractor\metrics
if exist metrics\ITHIM (
  mkdir extractor\metrics\ITHIM
  copy metrics\ITHIM\*.* extractor\metrics\ITHIM
)

:: offmodel
c:\windows\system32\Robocopy.exe /E offmodel extractor\offmodel

:: loaded network shapefiles
mkdir extractor\shapefile
copy shapefile extractor\shapefile

:success
echo ExtractKeyFiles into extractor for PBAU Complete
echo ENDED EXTRACTOR RUN  %DATE% %TIME% >> logs\feedback.rpt

:done
