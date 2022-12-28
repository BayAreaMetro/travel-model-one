# travel-model-one
The Metropolitan Transportation Commission (MTC) maintains a simulation model of typical weekday travel to assist in regional planning activities.  MTC makes the software and scripts necessary to implement the model as well as detailed model results available to the public.  Users of the model and/or the model's results are entirely responsible for the outcomes, interpretations, and conclusions they reach from the information.  Users of the MTC model or model results shall in no way imply MTC's support or review of their findings or analyses.

## Model Versions
The following model versions are available in the repository:

1. Version 0.3 -- Maintained in branch [`v03`](https://github.com/BayAreaMetro/travel-model-one/tree/v03).
2. Version 0.4 -- Maintained in branch [`v04`](https://github.com/BayAreaMetro/travel-model-one/tree/v04).
3. Version 0.5 -- Maintained in branch [`v05`](https://github.com/BayAreaMetro/travel-model-one/tree/v05).
3. Version 0.6 -- Maintained in branch [`v06`](https://github.com/BayAreaMetro/travel-model-one/tree/v06).
4. Version 1.5 -- Maintained in branch [`master`](https://github.com/BayAreaMetro/travel-model-one/tree/master).

Travel Model Two is also under development in a different repository: https://github.com/BayAreaMetro/travel-model-two

For additional details about the different versions, please see [here](https://github.com/BayAreaMetro/modeling-website/wiki/Development)
Any other branches are exploratory and not used in our planning work.

Please find a detailed User's Guide [here](https://github.com/BayAreaMetro/modeling-website/wiki/UsersGuide). 

# Running advanced air mobility (AAM) models on a new machine
I. Installations

1. Make sure anaconda2 or 3 scripts folder is in path

set path=%PATH%;C:\ProgramData\Anaconda3\Scripts

2. create new conda environment in python 2.7 for dependencies:

conda create --prefix=C:\ProgramData\Anaconda3\envs\py27tm1 python=2.7

if encountering errors, try copying
1)libcrypto-1_1-x64.dll
2)libssl-1_1-x64.dll
from ...\Anaconda3\Library\bin to ...\Anaconda3\DLLs

3. Activate the environment. 

activate py27tm1

4. Install packages

Follow MTC recommendation to download .whl file and install
https://github.com/BayAreaMetro/modeling-website/wiki/ComputingEnvironment
https://www.lfd.uci.edu/~gohlke/pythonlibs/

pip install E:\Projects\Clients\gm\models\python_packages\Shapely-1.6.4.post2-cp27-cp27m-win_amd64.whl
pip install E:\Projects\Clients\gm\models\python_packages\numpy-1.16.6+mkl-cp27-cp27m-win_amd64.whl
pip install E:\Projects\Clients\gm\models\python_packages\pandas-0.24.2-cp27-cp27m-win_amd64.whl
pip install E:\Projects\Clients\gm\models\python_packages\SimpleParse-2.2.0-cp27-cp27m-win_amd64.whl
pip install E:\Projects\Clients\gm\models\python_packages\xlrd-2.0.1-py2.py3-none-any.whl
pip install E:\Projects\Clients\gm\models\python_packages\xlwt-1.3.0-py2.py3-none-any.whl
pip install E:\Projects\Clients\gm\models\python_packages\xlutils-2.0.0-py2.py3-none-any.whl
pip install E:\Projects\Clients\gm\models\python_packages\pywin32-228-cp27-cp27m-win_amd64.whl
pip install E:\Projects\Clients\gm\models\python_packages\rpy2-2.7.8-cp27-none-win_amd64.whl
pip install E:\Projects\Clients\gm\models\python_packages\Rtree-0.9.3-cp27-cp27m-win_amd64.whl
pip install E:\Projects\Clients\gm\models\python_packages\XlsxWriter-1.2.7-py2.py3-none-any.whl

conda install geopandas
pip install dbfpy

if getting this error ImportError: Missing required dependencies ['pytz'], try
pip install python-dateutil pytz --force-reinstall --upgrade

5. make sure that the VoyagerAPI is installed

https://communities.bentley.com/products/mobility-simulation-analytics/m/cube-files/275055
path is set in \ctramp\runtime\SetPath.bat

6. make sure that network-wrangler is in your path. First clone network-wrangler to your repository using tortoise git:

https://github.com/BayAreaMetro/NetworkWrangler.git

then make sure it is added to the PYTHONPATH in SetPath.bat

7. make sure utils directory is on machine and point to gawk executable in SetPath.bat

8. make sure COMPATH, R_LIB, PYTHON_PATH, RUNTIME, PATH, and M_DIR in SetPath.bat are updated

SET COMMPATH=%MODEL_DIR%
set PYTHON_PATH=C:\ProgramData\Anaconda3
set RUNTIME=%CD%\CTRAMP\runtime
set PATH=%RUNTIME%;%JAVA_PATH%\bin;%TPP_PATH%;%GAWK_PATH%\bin;%PYTHON_PATH%\envs\py27tm1;%PYTHON_PATH%\condabin;%PYTHON_PATH%\envs
set M_DIR=E:\Projects\Clients\gm\models\2035_TM152_FBP_Plus_24

9. import NetworkWrangler

https://github.com/BayAreaMetro/modeling-website/wiki/Network-Building-with-NetworkWrangler#build-a-future

II. Steps for Results Summary (not necessary for model run)

1. Install R packages scales, dplyr, shapes, tidyr

2. If running RunResults.py (currently commented), update travel-model-one-master path to E:\\Projects\\Clients\\gm\\models\\travel-model-one\\

3. pip install these packages
pip install simpledbf
pip install xlwings
pip install openpyxl
If getting ImportError: No module named win32api, try pip install --upgrade pywin32==224

III. Set up and run base model without AAM

1. Create a new folder named 2035_TM152_FBP_Plus_24
2. Run the following command (conda env is activated in RunModel.bat, so it's not necessary to activate env prior to the model run)

cd /d E:\Projects\Clients\gm\models\2035_TM152_FBP_Plus_24
SetUpModel_2035_TM152_FBP_Plus_24.bat
RunModel.bat

IV. Set up AAM model run
1. update path and run Num_tours_sorted.ipynb
2. update path and run k-means.ipynb
3. update path and run generate_transitLines.ipynb
4. Open freeflow.net in Cube -> Play Edit Log -> AAM_nodes.log in INPUT\2035_TM152_FBP_Plus_24_aam_50v\hwy, Save
5. create a new folder 2035_TM152_FBP_Plus_24_aam_50v_500cpm (50 vertiports, AAM fare 500 cents per mile) in E:\Projects\Clients\gm\models
6. Copy SetUpModel_2035_TM152_FBP_Plus_24_aam_50v.bat from a previous run to this folder and update AAM_INPUT path

V. Run AAM model
1. Run the following command
cd /d E:\Projects\Clients\gm\models\2035_TM152_FBP_Plus_24_aam_50v_500cpm
SetUpModel_2035_TM152_FBP_Plus_24_aam_50v.bat (copies all files and add AAM input files)
RunModel.bat

VI. Set up and run fare sensitivity scenario on the same AAM network (only runs the final iteration)
1. Copy AAM full run, remove output folder, metrics folder, extractor folder, iter0 and iter1 folder in hwy and trn folder, and nonres\airport_by_mode_TOD.csv
2. Change the folder name based on naming convention 2035_TM152_FBP_Plus_24_aam_50v_800cpm
3. Copy RunCoreSummariesShortRun.bat, RunLogsumsShortRun.bat, RunMetricsShortRun.bat, RunScenarioMetricsShortRun.bat and CTRAMP\RunIterationShortRun.bat
4. Update Project.Directory and AAM.cost.per.mile in accessibilities.properties, logsums.properties, and mtcTourBased.properties in CTRAMP\runtime
	-AAM.cost.per.mile is in year 2000 cents (496), while fare in folder name (800) is in year 2019 cents
5. Update AAM.costPerMile in CTRAMP\scripts\block\AirportModeChoice.block (4.96, unit: year 2000 dollars per mile)
6. Copy and run RunAAMModel.bat

VII. Results Summary
1. Save dist_list_50v.csv and taz-superdistrict-county.csv in analysis\Inputs
2. Run Summarize_trips_TM1.5_AAM_50v_500cpm.ipynb
