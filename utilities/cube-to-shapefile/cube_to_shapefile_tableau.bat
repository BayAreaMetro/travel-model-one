REM This batch script runs the cube_to_shapefile.py script for all specified baselines and projects
REM This creates a "shapefile" folder in the OUTPUT folder of each baseline/project
REM It also copies the TransitNetworkViewer.twb file from github and renames it to TransitNetworkViewer_projectrunID.twb
REM Note: This needs to be run from a machine that has arcpy and access to mainmodel

@echo off

cd L:\RTP2021_PPA\Crossings

for /d %%x in (

				1_Crossings1\2050_TM151_PPA_RT_07_1_Crossings1_00
				1_Crossings1\2050_TM151_PPA_CG_07_1_Crossings1_01
				1_Crossings1\2050_TM151_PPA_BF_07_1_Crossings1_01

				1_Crossings2\2050_TM151_PPA_RT_07_1_Crossings2_00
				1_Crossings2\2050_TM151_PPA_CG_07_1_Crossings2_00
				1_Crossings2\2050_TM151_PPA_BF_07_1_Crossings2_00

				1_Crossings3\2050_TM151_PPA_RT_07_1_Crossings3_01
				1_Crossings3\2050_TM151_PPA_CG_07_1_Crossings3_00
				1_Crossings3\2050_TM151_PPA_BF_07_1_Crossings3_00

				1_Crossings4\2050_TM151_PPA_RT_07_1_Crossings4_01
				1_Crossings4\2050_TM151_PPA_CG_07_1_Crossings4_00
				1_Crossings4\2050_TM151_PPA_BF_07_1_Crossings4_00

				1_Crossings4\2050_TM151_PPA_RT_07_1_Crossings4_05
				1_Crossings4\2050_TM151_PPA_CG_07_1_Crossings4_06
				1_Crossings4\2050_TM151_PPA_BF_07_1_Crossings4_06

				1_Crossings5\2050_TM151_PPA_RT_07_1_Crossings5_00
				1_Crossings5\2050_TM151_PPA_CG_07_1_Crossings5_00
				1_Crossings5\2050_TM151_PPA_BF_07_1_Crossings5_00

				1_Crossings6\2050_TM151_PPA_RT_07_1_Crossings6_00
				1_Crossings6\2050_TM151_PPA_CG_07_1_Crossings6_00
				1_Crossings6\2050_TM151_PPA_BF_07_1_Crossings6_00

				1_Crossings7\2050_TM151_PPA_RT_07_1_Crossings7_01
				1_Crossings7\2050_TM151_PPA_CG_07_1_Crossings7_00
				1_Crossings7\2050_TM151_PPA_BF_07_1_Crossings7_00
				)	do (
		echo ==================================================================
		echo ==================================================================
		echo Running cube_to_shapefile for %%x...
		echo ==================================================================
		echo ==================================================================
		
		timeout 3

		cd %%x\OUTPUT


		if exist shapefile (
			echo Shapefile folder already exists for %%x
		) else (
			mkdir shapefile
			cd shapefile
			set PATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3;C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\Scripts
			python \\mainmodel\MainModelShare\travel-model-one-master\utilities\cube-to-shapefile\cube_to_shapefile.py --linefile ..\..\trn\transitLines.lin --trn_stop_info "M:\Application\Model One\Networks\TM1_2015_Base_Network\Node Description.xls" --loadvol_dir ..\trn --transit_crowding ..\metrics\transit_crowding_complete.csv ..\avgload5period.net
			echo Copying TransitNetworkViewer.twb to the folder...
			if not x%%x:\==%%x (
				FOR /f "tokens=1,2 delims=\ " %%a IN ("%%x") do (
					copy /y "\\mainmodel\MainModelShare\travel-model-one-master\utilities\cube-to-shapefile\TransitNetworkViewer.twb" ^
							"TransitNetworkViewer_%%b.twb")
			) else (
				copy /y "\\mainmodel\MainModelShare\travel-model-one-master\utilities\cube-to-shapefile\TransitNetworkViewer.twb" "TransitNetworkViewer_%%x.twb"
			)
			echo Shapefile folder successfully created for %%x
		)
		cd M:\Application\Model One\RTP2021\ProjectPerformanceAssessment\Projects
		)
		
pause
