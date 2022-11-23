# Used to created python 3.10 conda environment for TM1.5 run
# note: though creating conda environment directly from an environment config file is more straightforward, some python packages need to be installed from the .whl stored at "M:\Software\Python\". Therefore, recommand calling the following commands in Anaconda prompt to install the python 3.10 environment for TM1.5:

conda create --name tm15-python310 python=3.10
conda activate tm15-python310

# install packages for NetworkWrangler(https://github.com/BayAreaMetro/modeling-website/wiki/Network-Building-with-NetworkWrangler#step-3-install-the-required-python-packages-into-your-conda-environment)
pip install M:\Software\Python\SimpleParse-2.2.2-cp310-cp310-win_amd64.whl M:\Software\Python\pywin32-304.0-cp310-cp310-win_amd64.whl M:\Software\Python\pandas-1.4.3-cp310-cp310-win_amd64.whl
pip install xlrd

# install NetworkWrangler (ran `git pull` in here to make sure it's up to date)
cd C:\Users\mtcpb\Documents\GitHub\NetworkWrangler
pip install -e .

# for notify-slack
pip install requests

# for RuntimeConfiguration.py
pip install xlwt xlutils

# for csvToDbf.py
pip install dbfpy3

# for transitcrowding.py
pip install simpledbf

# for RunResults.py
pip install xlwings xlsxlwriter openpyxl