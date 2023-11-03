::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: ExtractKeyFiles.bat
::
:: MS-DOS batch file to extract key model files from various model run directories
:: for quick exporting for data summary.
::
:: lmz - Create version for PBAU (Plan Bay Area Update)
::
:: This just pulls output into OUTPUT\
::
:: See also CopyFilesToM.bat, which is meant to run afterwards
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo STARTED OUTPUT RUN  %DATE% %TIME% >> logs\feedback.rpt

:: Create the needed directories
mkdir OUTPUT

:: Assume this is set already
:: set ITER=3

:: Highway assignment results
copy hwy\iter%ITER%\avgload5period.net            OUTPUT\avgload5period.net
copy hwy\iter%ITER%\avgload5period.csv            OUTPUT\avgload5period.csv
copy hwy\iter%ITER%\avgload5period_vehclasses.csv OUTPUT\avgload5period_vehclasses.csv

:: Transit assignment results
mkdir OUTPUT\trn
copy trn\TransitAssignment.iter3\trnline*.csv    OUTPUT\trn
copy trn\trnlink*.dbf                            OUTPUT\trn
copy trn\trnlink.csv                             OUTPUT\trn
copy trn\trnline.csv                             OUTPUT\trn
copy trn\quickboards.xls                         OUTPUT\trn

:: Demand results
copy main\householdData_%ITER%.csv OUTPUT\main\householdData_%ITER%.csv
copy main\personData_%ITER%.csv    OUTPUT\main\personData_%ITER%.csv
copy main\indivTripData_%ITER%.csv OUTPUT\main\indivTripData_%ITER%.csv
copy main\indivTourData_%ITER%.csv OUTPUT\main\indivTourData_%ITER%.csv
copy main\jointTripData_%ITER%.csv OUTPUT\main\jointTripData_%ITER%.csv
copy main\jointTourData_%ITER%.csv OUTPUT\main\jointTourData_%ITER%.csv
copy main\wsLocResults_%ITER%.csv  OUTPUT\main\wsLocResults_%ITER%.csv

:: Report results
copy logs\HwySkims.debug  OUTPUT\HwySkims.debug
copy logs\feedback.rpt    OUTPUT\feedback.rpt
copy logs\SpeedErrors.log OUTPUT\SpeedErrors.log

:: Skim databases
:: mkdir OUTPUT\skimDB
:: copy database\*.csv OUTPUT\skimDB\*.csv

:: Trip tables
mkdir OUTPUT\main
copy main\tripsEA.tpp OUTPUT\main
copy main\tripsAM.tpp OUTPUT\main
copy main\tripsMD.tpp OUTPUT\main
copy main\tripsPM.tpp OUTPUT\main
copy main\tripsEV.tpp OUTPUT\main
copy main\ShadowPricing_7.csv OUTPUT\main

mkdir OUTPUT\nonres
copy nonres\ixDaily2015.tpp OUTPUT\nonres
copy nonres\ixDailyx4.tpp   OUTPUT\nonres

:: copy skims\hwyskmEA.tpp OUTPUT\emfac\hwyskmEA.tpp
:: copy skims\hwyskmAM.tpp OUTPUT\emfac\hwyskmAM.tpp
:: copy skims\hwyskmMD.tpp OUTPUT\emfac\hwyskmMD.tpp
:: copy skims\hwyskmPM.tpp OUTPUT\emfac\hwyskmPM.tpp
:: copy skims\hwyskmEV.tpp OUTPUT\emfac\hwyskmEV.tpp

:: copy skims\com_hwyskimEA.tpp OUTPUT\emfac\com_hwyskimEA.tpp
:: copy skims\com_hwyskimAM.tpp OUTPUT\emfac\com_hwyskimAM.tpp
:: copy skims\com_hwyskimMD.tpp OUTPUT\emfac\com_hwyskimMD.tpp
:: copy skims\com_hwyskimPM.tpp OUTPUT\emfac\com_hwyskimPM.tpp
:: copy skims\com_hwyskimEV.tpp OUTPUT\emfac\com_hwyskimEV.tpp

:: copy nonres\tripsTrkEA.tpp OUTPUT\emfac\tripsTrkEA.tpp
:: copy nonres\tripsTrkAM.tpp OUTPUT\emfac\tripsTrkAM.tpp
:: copy nonres\tripsTrkMD.tpp OUTPUT\emfac\tripsTrkMD.tpp
:: copy nonres\tripsTrkPM.tpp OUTPUT\emfac\tripsTrkPM.tpp
:: copy nonres\tripsTrkEV.tpp OUTPUT\emfac\tripsTrkEV.tpp

:: Save the control file
copy CTRAMP\runtime\mtcTourBased.properties OUTPUT\mtcTourBased.properties
copy CTRAMP\runtime\mtcTourBased.properties OUTPUT\logsums.properties

:: Accessibility files
mkdir OUTPUT\accessibilities
copy accessibilities\nonMandatoryAccessibilities.csv OUTPUT\accessibilities
copy accessibilities\mandatoryAccessibilities.csv    OUTPUT\accessibilities
copy skims\accessibility.csv                         OUTPUT\accessibilities

:: Accessibility files - model results
mkdir OUTPUT\logsums
copy logsums\householdData_%ITER%.csv                OUTPUT\logsums
copy logsums\personData_%ITER%.csv                   OUTPUT\logsums
copy logsums\indivTripData_%ITER%.csv                OUTPUT\logsums
copy logsums\indivTourData_%ITER%.csv                OUTPUT\logsums
copy logsums\wsLocResults_%ITER%.csv                 OUTPUT\logsums
:: summaries from logsumJoiner
copy logsums\shopDCLogsum.csv                        OUTPUT\logsums
copy logsums\tour_shopDCLogsum.csv                   OUTPUT\logsums
copy logsums\workDCLogsum.csv                        OUTPUT\logsums
copy logsums\person_workDCLogsum.csv                 OUTPUT\logsums
copy logsums\mandatoryAccessibilities.csv            OUTPUT\logsums
copy logsums\nonMandatoryAccessibilities.csv         OUTPUT\logsums

:: Core summaries
mkdir OUTPUT\core_summaries
copy core_summaries\*.*                              OUTPUT\core_summaries
mkdir OUTPUT\updated_output
copy updated_output\*.*                              OUTPUT\updated_output

:: metrics
mkdir OUTPUT\metrics
copy metrics OUTPUT\metrics
if exist metrics\ITHIM (
  mkdir OUTPUT\metrics\ITHIM
  copy metrics\ITHIM\*.* OUTPUT\metrics\ITHIM
)

:success
echo ExtractKeyFiles into OUTPUT for PBAU Complete
echo ENDED OUTPUT RUN  %DATE% %TIME% >> logs\feedback.rpt

:done