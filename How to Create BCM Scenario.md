# Creating BiCounty Model Scenario

## Prerequisites:

1. ### Correct version of python
   BiCounty Model setup requires two versions of python: the network setup uses python 2.7 and calibration and validation uses python version >3.7. Install python 2.7 separately in a new environment. Newer versions of python are installed automatically when installing python through Anaconda.
	Install Anaconda. The newest version of Anaconda is currently version 22.xx. There is still an [unresolved issue in this version regarding openSSL](https://github.com/conda/conda/issues/11795), which is the primary package responsible for downloading and installing various packages. To avoid the complicated solution, [download and install an older build of Anaconda (e.g., 4.1x) from the archives](https://repo.anaconda.com/archive/). A version that works is Anaconda3-2022.05-Windows-x86_64.exe.  
	Create new environment py27 for python version 2.7 from anaconda prompt using  
    <code> conda create -y -n py27 python=2.7 </code>  
	Activate py27 by typing activate py27 on anaconda prompt
	Install the following packages:   
        dbfpy, numpy, simpleparse, openpyxl, xlrd, xlwt, xlutils, requests, pandas using pip   
        <code> pip install dbfpy, numpy, simpleparse, openpyxl, xlrd, xlwt, xlutils, requests, pandas </code>

2. ### Add HOME_IP_ADDRESS to PATH
   Open command prompt. Type <code>ipconfig /all </code>
   Go to advanced system settings>Advanced>Environmental Variables..  Add new system variable with the name <b> HOST_IP_ADDRESS </b> and value as the host name.
3. ### Install GAWK
   	Download gawk from http://gnuwin32.sourceforge.net/downlinks/gawk.php 
	Run the exe file as Administrator. Install it on a location other than Program Files (x86), because it crashes otherwise.
4. ### Install Github Desktop
    Easier to work with the correct branches of Travel Model.
5. ### Clone NetworkWrangler 1.0 from MTC's github repo
   Clone https://github.com/BayAreaMetro/NetworkWrangler in Documents/Github/NetworkWrangler
6. ### Install Voyager API
7. ### Install R

## Creating Scenario

### Step 1: Clone Travel Model One to desktop:
From github desktop, go to File > Clone Repository > URL, paste https://github.com/wsp-sag/travel-model-one  
Clone the repository to a directory of your choosing. When prompted, select Contribute to wsp-sag/travel-model-one instead of BayAreaMetro/travel-model-one
### Step 2: Switch branch to bicounty_develop:
From github desktop, navigate to to the Current Branch tab and select <b> bicounty_develop </b>. This is the branch where all the model developments are currently processed. Once the model is finalized, the changes will be pulled in to the <b>bicounty</b> branch which will be an offshoot of the MTC's Travel Model 1 repository.
### Step 3: Create Scenario Folder (should automate in a future version):
Create Folder named 2015_BaseY_XXX2015, the config files require at least 16 characters in the model run folder. This is the Base folder.This will be the <b> M Directory </b>.
Naming convention:  
	<b> MODEL_YEAR </b>=%myfolder:~0,4%  
	<b>PROJECT</b>=%myfolder:~11,3%, PROJECT in one of [IPA, DBP, FBP, PPA]  
	<b>FUTURE_ABBR</b>=%myfolder:~15,2%; FUTURE_ABBR is one of [RT,CG,BF]  
### Step 4: Create folder named COMMPATH
The folder should be created in the same directory as the model directory
### Step 4: Edit the SetUpModel_PBA50.bat:
Go into the locally cloned travel-model-one repository. Inside model-files, open the SetUpModel_PBA50.bat batch file in any standard text file editor (notepad, notepad++, visual studio code) and edit to point to correct locations of the input files. <b> Make Sure to Point to Your Own SharePoint path</b>
### Step 5: Run SetUpModel_PBA50.bat:
Open command prompt in the local clone of travel-model-one and run the SetUpModel_PBA50.bat file. This will copy over the scripts and input files to the Model/Scenario Directory.
### Step 6: Edit the SetPath.bat:
This file points to the COMMPATH, java development kit, GAWK binary executable file, R and R libraries, python, RunTPP executable from CitiLabs etc. Edit the CTRAMP>runtime>SetPath.bat file for your specific set up. 
### Step 7: Edit the RunTimeConfiguration.py file:
Edit CTRAMP>scripts>preprocess>RunTimeConfiguration.py file on lines 530 and 574 to include the local computer name in the hostname list. Copy it from System settings.
### Step 8: Run the RunModel.bat file:
The current iteration of RunModel.bat file works with the modified scripts. Open a command prompt from the Model Directory and run the batch file to run a simulation.