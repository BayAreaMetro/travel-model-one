# Creating BiCounty Model Scenario

## Prerequisites:

1. ### Map the SAG Drive as Z:
	The SAG storage drive contains the warmstart inputs, static inputs and a copy of the model repository set to the bicounty_develop branch (base branch for all BCM development).
	It also contains the python, R, GAWK setup to run BCM. The path to all the necessary programs are set in the model-files\runtime\SetPath.bat script.
2. ### Install Github Desktop
    Easier to work with the correct branches of Travel Model.
3. ### Clone NetworkWrangler 1.0 from MTC's github repo
   Clone https://github.com/BayAreaMetro/NetworkWrangler in Documents/Github/NetworkWrangler

## Creating Scenario

### Step 1: Clone Travel Model One to desktop:
From github desktop, go to File > Clone Repository > URL, paste https://github.com/wsp-sag/travel-model-one  
Clone the repository to a directory of your choosing. When prompted, select Contribute to wsp-sag/travel-model-one instead of BayAreaMetro/travel-model-one
### Step 2: Switch branch to bicounty_develop:
From github desktop, navigate to to the Current Branch tab and select <b> bicounty_develop </b>. This is the branch where all the model developments are currently processed. Once the model is finalized, the changes will be pulled in to the <b>bicounty</b> branch which will be an offshoot of the MTC's Travel Model 1 repository.

### Step 3: Edit the SetUpModel_PBA50.bat
Open the SetUpModel_PBA50.bat in notepad++ and edit Line 15 to point to the locally cloned BCM repository.
set GITHUB_DIR=Z:\projects\ccta\31000190\Jawad\travel-model-one

### Step 4: Edit the SetPath.bat:
This file points to the COMMPATH, java development kit, GAWK binary executable file, R and R libraries, python, RunTPP executable from CitiLabs etc. Edit the CTRAMP>runtime>SetPath.bat file for your specific set up. 

* set JAVA_PATH=C:\Program Files\Java\jdk1.8.0_181
* set TPP_PATH=C:\Program Files\Citilabs\VoyagerFileAPI


### Step 7: Run SetUpModel_PBA50.bat:
Open command prompt in the local clone of travel-model-one and run the SetUpModel_PBA50.bat file. This will copy over the scripts and input files to the Model/Scenario Directory. Alternatively, double-click on the createScenario.bat file. This will also create a log file.

### Step 8: Run the RunModel.bat file:
The current iteration of RunModel.bat file works with the modified scripts. Open a command prompt from the Model Directory and run the batch file to run a simulation. You can also copy the clickToRunModel.bat file to your model folder and double-click to run the setup.

## Alternate setup
Z:\projects\ccta\31000190\Jawad\travel-model-one is the clone of the BCM repo that is set to the most updated branch. You can directly use the SetUpModel_PBA50.bat file to create a scenario in the VDI.