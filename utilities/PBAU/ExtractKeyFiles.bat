::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: ExtractKeyFiles.bat
::
:: MS-DOS batch file to extract key model files from various model run directories
:: for quick exporting for data summary.
::
:: lmz - Create version for PBAU (Plan Bay Area Update)
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:: Create the needed directories
mkdir extractor
mkdir extractor\INPUT
mkdir extractor\OUTPUT

:: Set the last iteration variable
set last=3

:: RunModel
copy RunModel.bat extractor\RunModel.bat

:: Input land use file and networks
copy INPUT\params.properties extractor\INPUT
copy landuse\tazData.csv extractor\INPUT\tazData.csv
copy INPUT\hwy extractor\INPUT
copy INPUT\trn extractor\INPUT

:: Highway assignment results
copy hwy\iter3\avgload5period.net extractor\OUTPUT\avgload5period.net
copy hwy\iter3\avgload5period.csv extractor\OUTPUT\avgload5period.csv

:: Transit assignment results
mkdir extractor\OUTPUT\trn
copy trn\trnline*.csv extractor\OUTPUT\trn\trnline*.csv
copy trn\trnlink*.dbf extractor\OUTPUT\trn\trnlink*.dbf

:: Demand results
:: copy main\householdData_%last%.csv extractor\householdData_%last%.csv 
:: copy main\personData_%last%.csv extractor\personData_%last%.csv 
:: copy main\indivTripData_%last%.csv extractor\indivTripData_%last%.csv 
:: copy main\indivTourData_%last%.csv extractor\indivTourData_%last%.csv 
:: copy main\jointTripData_%last%.csv extractor\jointTripData_%last%.csv 
:: copy main\jointTourData_%last%.csv extractor\jointTourData_%last%.csv 
:: copy main\wsLocResults_%last%.csv extractor\wsLocResults_%last%.csv 

:: Report results
copy logs\HwySkims.debug extractor\OUTPUT\HwySkims.debug
copy logs\feedback.rpt extractor\OUTPUT\feedback.rpt
copy logs\SpeedErrors.log extractor\OUTPUT\SpeedErrors.log

:: Skim databases
:: copy database\*.csv extractor\skimDB\*.csv

:: Trip tables
mkdir extractor\OUTPUT\main
copy main\tripsEA.tpp extractor\OUTPUT\main
copy main\tripsAM.tpp extractor\OUTPUT\main
copy main\tripsMD.tpp extractor\OUTPUT\main
copy main\tripsPM.tpp extractor\OUTPUT\main
copy main\tripsEV.tpp extractor\OUTPUT\main

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
mkdir extractor\OUTPUT\accessibilities
copy accessibilities\nonMandatoryAccessibilities.csv extractor\OUTPUT\accessibilities
copy accessibilities\mandatoryAccessibilities.csv extractor\OUTPUT\accessibilities
copy skims\accessibility.csv extractor\OUTPUT\accessibilities

:: metrics
mkdir extractor\OUTPUT\metrics
copy metrics extractor\OUTPUT\metrics

rem ExtractKeyFiles for PBAU Complete
