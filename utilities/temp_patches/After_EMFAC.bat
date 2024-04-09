REM with the fixed create_EMFAC_custom_activity_file.py, we get updated emfac results. The script was to post process it to get emfac_ghg.csv.
REM see full instructions https://github.com/BayAreaMetro/modeling-website/wiki/From-Travel-Model-To-EMFAC (How to generate a regional level summary after EMFAC is done)

cd /d A:\Projects\2035_TM152_NGF_NP02_BPALTsegmented_03_SensDyn00_2
set M_DIR=L:\Application\Model_One\NextGenFwys\Scenarios\2035_TM152_NGF_NP02_BPALTsegmented_03_SensDyn00_2
python ctramp/scripts/emfac/emfac_postproc.py SB375