:: convert-csv-to-dbf.bat
::
:: MS-DOS batch file that uses R to convert CSV files to DBF.

set CODE_DIR=D:\files\GitHub\travel-model-one\utilities\taz-data-csv-to-dbf\
set R_DIR=C:\Program Files\R\R-3.1.3\bin\x64

set PATH=%R_DIR%;%PATH%

set YEAR_ARRAY=2010 2015 2020 2025 2030 2035 2040

for %%X in (%YEAR_ARRAY%) do (
	
	echo Converting %%X ...
	copy tazData%%X.csv input.csv
	call Rscript.exe --vanilla %CODE_DIR%\taz-data-csv-to-dbf.R
	copy output.dbf tazData%%X.dbf
	del output.dbf
	echo -------------------------------------------

	)
