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
copy hwy\iter%ITER%\avgload5period.net extractor\avgload5period.net
copy hwy\iter%ITER%\avgload5period.csv extractor\avgload5period.csv

:: Transit assignment results
mkdir extractor\trn
copy trn\trnline*.csv    extractor\trn\trnline*.csv
copy trn\trnlink*.dbf    extractor\trn\trnlink*.dbf
copy trn\quickboards.xls extractor\trn\quickboards.xls

:: Demand results
:: copy main\householdData_%ITER%.csv extractor\householdData_%ITER%.csv
:: copy main\personData_%ITER%.csv    extractor\personData_%ITER%.csv
:: copy main\indivTripData_%ITER%.csv extractor\indivTripData_%ITER%.csv
:: copy main\indivTourData_%ITER%.csv extractor\indivTourData_%ITER%.csv
:: copy main\jointTripData_%ITER%.csv extractor\jointTripData_%ITER%.csv
:: copy main\jointTourData_%ITER%.csv extractor\jointTourData_%ITER%.csv
:: copy main\wsLocResults_%ITER%.csv  extractor\wsLocResults_%ITER%.csv

:: Report results
copy logs\HwySkims.debug  extractor\HwySkims.debug
copy logs\feedback.rpt    extractor\feedback.rpt
copy logs\SpeedErrors.log extractor\SpeedErrors.log

:: Skim databases
:: copy database\*.csv extractor\skimDB\*.csv

:: Trip tables
mkdir extractor\main
copy main\tripsEA.tpp extractor\main
copy main\tripsAM.tpp extractor\main
copy main\tripsMD.tpp extractor\main
copy main\tripsPM.tpp extractor\main
copy main\tripsEV.tpp extractor\main

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
:: copy CTRAMP\runtime\mtcTourBased.properties extractor\mtcTourBased.properties

:: Accessibility files
mkdir extractor\accessibilities
copy accessibilities\nonMandatoryAccessibilities.csv extractor\accessibilities
copy accessibilities\mandatoryAccessibilities.csv    extractor\accessibilities
copy skims\accessibility.csv                         extractor\accessibilities

mkdir extractor\core_summaries
copy core_summaries\AccessibilityMarkets.*           extractor\core_summaries

:: metrics
mkdir extractor\metrics
copy metrics extractor\metrics

:success
echo ExtractKeyFiles into extractor for PBAU Complete
echo ENDED EXTRACTOR RUN  %DATE% %TIME% >> logs\feedback.rpt

:done