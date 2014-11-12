# -*- coding: utf-8 -*-
"""
Created on Fri Sep 06 11:06:32 2013

@author: dvauti
"""
import sys
proj = sys.argv

import csv

input_file_name = raw_input('Input File Name: ')
input_data = list(csv.reader(open(input_file_name, 'rb')))

annualization = 300
if proj == 0:
    project_id = input_data[1][1]
else:
    project_id = input_data[2][1]
project_file_name = project_id + '.csv'


# IMPORT TRAVEL MODEL OUTPUTS FROM CSV FILE



data = list(csv.reader(open(project_file_name, 'rb')))

TMO_trtrips_wlk_com_wlk = float(data[1][1])
TMO_trtrips_drv_com_wlk = float(data[2][1])
TMO_trtrips_wlk_com_drv = float(data[3][1])
TMO_trtrips_wlk_hvy_wlk = float(data[4][1])
TMO_trtrips_drv_hvy_wlk = float(data[5][1])
TMO_trtrips_wlk_hvy_drv = float(data[6][1])
TMO_trtrips_wlk_exp_wlk = float(data[7][1])
TMO_trtrips_drv_exp_wlk = float(data[8][1])
TMO_trtrips_wlk_exp_drv = float(data[9][1])
TMO_trtrips_wlk_lrf_wlk = float(data[10][1])
TMO_trtrips_drv_lrf_wlk = float(data[11][1])
TMO_trtrips_wlk_lrf_drv = float(data[12][1])
TMO_trtrips_wlk_loc_wlk = float(data[13][1])
TMO_trtrips_drv_loc_wlk = float(data[14][1])
TMO_trtrips_wlk_loc_drv = float(data[15][1])

TMO_ivtt_wlk_com_wlk = float(data[1][2])
TMO_ivtt_drv_com_wlk = float(data[2][2])
TMO_ivtt_wlk_com_drv = float(data[3][2])
TMO_ivtt_wlk_hvy_wlk = float(data[4][2])
TMO_ivtt_drv_hvy_wlk = float(data[5][2])
TMO_ivtt_wlk_hvy_drv = float(data[6][2])
TMO_ivtt_wlk_exp_wlk = float(data[7][2])
TMO_ivtt_drv_exp_wlk = float(data[8][2])
TMO_ivtt_wlk_exp_drv = float(data[9][2])
TMO_ivtt_wlk_lrf_wlk = float(data[10][2])
TMO_ivtt_drv_lrf_wlk = float(data[11][2])
TMO_ivtt_wlk_lrf_drv = float(data[12][2])
TMO_ivtt_wlk_loc_wlk = float(data[13][2])
TMO_ivtt_drv_loc_wlk = float(data[14][2])
TMO_ivtt_wlk_loc_drv = float(data[15][2])

TMO_ovtt_wlk_com_wlk = float(data[1][3])
TMO_ovtt_drv_com_wlk = float(data[2][3])
TMO_ovtt_wlk_com_drv = float(data[3][3])
TMO_ovtt_wlk_hvy_wlk = float(data[4][3])
TMO_ovtt_drv_hvy_wlk = float(data[5][3])
TMO_ovtt_wlk_hvy_drv = float(data[6][3])
TMO_ovtt_wlk_exp_wlk = float(data[7][3])
TMO_ovtt_drv_exp_wlk = float(data[8][3])
TMO_ovtt_wlk_exp_drv = float(data[9][3])
TMO_ovtt_wlk_lrf_wlk = float(data[10][3])
TMO_ovtt_drv_lrf_wlk = float(data[11][3])
TMO_ovtt_wlk_lrf_drv = float(data[12][3])
TMO_ovtt_wlk_loc_wlk = float(data[13][3])
TMO_ovtt_drv_loc_wlk = float(data[14][3])
TMO_ovtt_wlk_loc_drv = float(data[15][3])

TMO_iwait_wlk_com_wlk = float(data[1][4])
TMO_iwait_drv_com_wlk = float(data[2][4])
TMO_iwait_wlk_com_drv = float(data[3][4])
TMO_iwait_wlk_hvy_wlk = float(data[4][4])
TMO_iwait_drv_hvy_wlk = float(data[5][4])
TMO_iwait_wlk_hvy_drv = float(data[6][4])
TMO_iwait_wlk_exp_wlk = float(data[7][4])
TMO_iwait_drv_exp_wlk = float(data[8][4])
TMO_iwait_wlk_exp_drv = float(data[9][4])
TMO_iwait_wlk_lrf_wlk = float(data[10][4])
TMO_iwait_drv_lrf_wlk = float(data[11][4])
TMO_iwait_wlk_lrf_drv = float(data[12][4])
TMO_iwait_wlk_loc_wlk = float(data[13][4])
TMO_iwait_drv_loc_wlk = float(data[14][4])
TMO_iwait_wlk_loc_drv = float(data[15][4])

TMO_xfer_wlk_com_wlk = float(data[1][5])
TMO_xfer_drv_com_wlk = float(data[2][5])
TMO_xfer_wlk_com_drv = float(data[3][5])
TMO_xfer_wlk_hvy_wlk = float(data[4][5])
TMO_xfer_drv_hvy_wlk = float(data[5][5])
TMO_xfer_wlk_hvy_drv = float(data[6][5])
TMO_xfer_wlk_exp_wlk = float(data[7][5])
TMO_xfer_drv_exp_wlk = float(data[8][5])
TMO_xfer_wlk_exp_drv = float(data[9][5])
TMO_xfer_wlk_lrf_wlk = float(data[10][5])
TMO_xfer_drv_lrf_wlk = float(data[11][5])
TMO_xfer_wlk_lrf_drv = float(data[12][5])
TMO_xfer_wlk_loc_wlk = float(data[13][5])
TMO_xfer_drv_loc_wlk = float(data[14][5])
TMO_xfer_wlk_loc_drv = float(data[15][5])

TMO_wlkaceg_wlk_com_wlk = float(data[1][6])
TMO_wlkaceg_drv_com_wlk = float(data[2][6])
TMO_wlkaceg_wlk_com_drv = float(data[3][6])
TMO_wlkaceg_wlk_hvy_wlk = float(data[4][6])
TMO_wlkaceg_drv_hvy_wlk = float(data[5][6])
TMO_wlkaceg_wlk_hvy_drv = float(data[6][6])
TMO_wlkaceg_wlk_exp_wlk = float(data[7][6])
TMO_wlkaceg_drv_exp_wlk = float(data[8][6])
TMO_wlkaceg_wlk_exp_drv = float(data[9][6])
TMO_wlkaceg_wlk_lrf_wlk = float(data[10][6])
TMO_wlkaceg_drv_lrf_wlk = float(data[11][6])
TMO_wlkaceg_wlk_lrf_drv = float(data[12][6])
TMO_wlkaceg_wlk_loc_wlk = float(data[13][6])
TMO_wlkaceg_drv_loc_wlk = float(data[14][6])
TMO_wlkaceg_wlk_loc_drv = float(data[15][6])

TMO_auxwlk_wlk_com_wlk = float(data[1][7])
TMO_auxwlk_drv_com_wlk = float(data[2][7])
TMO_auxwlk_wlk_com_drv = float(data[3][7])
TMO_auxwlk_wlk_hvy_wlk = float(data[4][7])
TMO_auxwlk_drv_hvy_wlk = float(data[5][7])
TMO_auxwlk_wlk_hvy_drv = float(data[6][7])
TMO_auxwlk_wlk_exp_wlk = float(data[7][7])
TMO_auxwlk_drv_exp_wlk = float(data[8][7])
TMO_auxwlk_wlk_exp_drv = float(data[9][7])
TMO_auxwlk_wlk_lrf_wlk = float(data[10][7])
TMO_auxwlk_drv_lrf_wlk = float(data[11][7])
TMO_auxwlk_wlk_lrf_drv = float(data[12][7])
TMO_auxwlk_wlk_loc_wlk = float(data[13][7])
TMO_auxwlk_drv_loc_wlk = float(data[14][7])
TMO_auxwlk_wlk_loc_drv = float(data[15][7])

TMO_draceg_wlk_com_wlk = float(data[1][8])
TMO_draceg_drv_com_wlk = float(data[2][8])
TMO_draceg_wlk_com_drv = float(data[3][8])
TMO_draceg_wlk_hvy_wlk = float(data[4][8])
TMO_draceg_drv_hvy_wlk = float(data[5][8])
TMO_draceg_wlk_hvy_drv = float(data[6][8])
TMO_draceg_wlk_exp_wlk = float(data[7][8])
TMO_draceg_drv_exp_wlk = float(data[8][8])
TMO_draceg_wlk_exp_drv = float(data[9][8])
TMO_draceg_wlk_lrf_wlk = float(data[10][8])
TMO_draceg_drv_lrf_wlk = float(data[11][8])
TMO_draceg_wlk_lrf_drv = float(data[12][8])
TMO_draceg_wlk_loc_wlk = float(data[13][8])
TMO_draceg_drv_loc_wlk = float(data[14][8])
TMO_draceg_wlk_loc_drv = float(data[15][8])

TMO_autrips_da = float(data[23][1])
TMO_autrips_datoll = float(data[24][1])
TMO_autrips_sr2 = float(data[25][1])
TMO_autrips_sr2toll = float(data[26][1])
TMO_autrips_sr3 = float(data[27][1])
TMO_autrips_sr3toll = float(data[28][1])

TMO_avgtime_da = float(data[23][2])
TMO_avgtime_datoll = float(data[24][2])
TMO_avgtime_sr2 = float(data[25][2])
TMO_avgtime_sr2toll = float(data[26][2])
TMO_avgtime_sr3 = float(data[27][2])
TMO_avgtime_sr3toll = float(data[28][2])

TMO_avgdist_da = float(data[23][3])
TMO_avgdist_datoll = float(data[24][3])
TMO_avgdist_sr2 = float(data[25][3])
TMO_avgdist_sr2toll = float(data[26][3])
TMO_avgdist_sr3 = float(data[27][3])
TMO_avgdist_sr3toll = float(data[28][3])

# note that these costs will not be accurate for SGR testing work
TMO_avgcost_da = float(data[23][4])
TMO_avgcost_datoll = float(data[24][4])
TMO_avgcost_sr2 = float(data[25][4])
TMO_avgcost_sr2toll = float(data[26][4])
TMO_avgcost_sr3 = float(data[27][4])
TMO_avgcost_sr3toll = float(data[28][4])

TMO_wktrips = float(data[30][1])
TMO_bktrips = float(data[31][1])
TMO_wkavgtime = float(data[30][2])
TMO_bkavgtime = float(data[31][2])
TMO_wkavgdist = float(data[30][3])
TMO_bkavgdist = float(data[31][3])


TMO_VHT_da_ea = float(data[35][1])
TMO_VHT_da_am = float(data[36][1])
TMO_VHT_da_md = float(data[37][1])
TMO_VHT_da_pm = float(data[38][1])
TMO_VHT_da_ev = float(data[39][1])
TMO_VHT_sr2_ea = float(data[35][2])
TMO_VHT_sr2_am = float(data[36][2])
TMO_VHT_sr2_md = float(data[37][2])
TMO_VHT_sr2_pm = float(data[38][2])
TMO_VHT_sr2_ev = float(data[39][2])
TMO_VHT_sr3_ea = float(data[35][3])
TMO_VHT_sr3_am = float(data[36][3])
TMO_VHT_sr3_md = float(data[37][3])
TMO_VHT_sr3_pm = float(data[38][3])
TMO_VHT_sr3_ev = float(data[39][3])
TMO_VHT_sm_ea = float(data[35][4])
TMO_VHT_sm_am = float(data[36][4])
TMO_VHT_sm_md = float(data[37][4])
TMO_VHT_sm_pm = float(data[38][4])
TMO_VHT_sm_ev = float(data[39][4])
TMO_VHT_hv_ea = float(data[35][5])
TMO_VHT_hv_am = float(data[36][5])
TMO_VHT_hv_md = float(data[37][5])
TMO_VHT_hv_pm = float(data[38][5])
TMO_VHT_hv_ev = float(data[39][5])
TMO_VHT_datoll_ea = float(data[35][6])
TMO_VHT_datoll_am = float(data[36][6])
TMO_VHT_datoll_md = float(data[37][6])
TMO_VHT_datoll_pm = float(data[38][6])
TMO_VHT_datoll_ev = float(data[39][6])
TMO_VHT_sr2toll_ea = float(data[35][7])
TMO_VHT_sr2toll_am = float(data[36][7])
TMO_VHT_sr2toll_md = float(data[37][7])
TMO_VHT_sr2toll_pm = float(data[38][7])
TMO_VHT_sr2toll_ev = float(data[39][7])
TMO_VHT_sr3toll_ea = float(data[35][8])
TMO_VHT_sr3toll_am = float(data[36][8])
TMO_VHT_sr3toll_md = float(data[37][8])
TMO_VHT_sr3toll_pm = float(data[38][8])
TMO_VHT_sr3toll_ev = float(data[39][8])
TMO_VHT_smtoll_ea = float(data[35][9])
TMO_VHT_smtoll_am = float(data[36][9])
TMO_VHT_smtoll_md = float(data[37][9])
TMO_VHT_smtoll_pm = float(data[38][9])
TMO_VHT_smtoll_ev = float(data[39][9])
TMO_VHT_hvtoll_ea = float(data[35][10])
TMO_VHT_hvtoll_am = float(data[36][10])
TMO_VHT_hvtoll_md = float(data[37][10])
TMO_VHT_hvtoll_pm = float(data[38][10])
TMO_VHT_hvtoll_ev = float(data[39][10])

TMO_VMT_da_ea = float(data[43][1])
TMO_VMT_da_am = float(data[44][1])
TMO_VMT_da_md = float(data[45][1])
TMO_VMT_da_pm = float(data[46][1])
TMO_VMT_da_ev = float(data[47][1])
TMO_VMT_sr2_ea = float(data[43][2])
TMO_VMT_sr2_am = float(data[44][2])
TMO_VMT_sr2_md = float(data[45][2])
TMO_VMT_sr2_pm = float(data[46][2])
TMO_VMT_sr2_ev = float(data[47][2])
TMO_VMT_sr3_ea = float(data[43][3])
TMO_VMT_sr3_am = float(data[44][3])
TMO_VMT_sr3_md = float(data[45][3])
TMO_VMT_sr3_pm = float(data[46][3])
TMO_VMT_sr3_ev = float(data[47][3])
TMO_VMT_sm_ea = float(data[43][4])
TMO_VMT_sm_am = float(data[44][4])
TMO_VMT_sm_md = float(data[45][4])
TMO_VMT_sm_pm = float(data[46][4])
TMO_VMT_sm_ev = float(data[47][4])
TMO_VMT_hv_ea = float(data[43][5])
TMO_VMT_hv_am = float(data[44][5])
TMO_VMT_hv_md = float(data[45][5])
TMO_VMT_hv_pm = float(data[46][5])
TMO_VMT_hv_ev = float(data[47][5])
TMO_VMT_datoll_ea = float(data[43][6])
TMO_VMT_datoll_am = float(data[44][6])
TMO_VMT_datoll_md = float(data[45][6])
TMO_VMT_datoll_pm = float(data[46][6])
TMO_VMT_datoll_ev = float(data[47][6])
TMO_VMT_sr2toll_ea = float(data[43][7])
TMO_VMT_sr2toll_am = float(data[44][7])
TMO_VMT_sr2toll_md = float(data[45][7])
TMO_VMT_sr2toll_pm = float(data[46][7])
TMO_VMT_sr2toll_ev = float(data[47][7])
TMO_VMT_sr3toll_ea = float(data[43][8])
TMO_VMT_sr3toll_am = float(data[44][8])
TMO_VMT_sr3toll_md = float(data[45][8])
TMO_VMT_sr3toll_pm = float(data[46][8])
TMO_VMT_sr3toll_ev = float(data[47][8])
TMO_VMT_smtoll_ea = float(data[43][9])
TMO_VMT_smtoll_am = float(data[44][9])
TMO_VMT_smtoll_md = float(data[45][9])
TMO_VMT_smtoll_pm = float(data[46][9])
TMO_VMT_smtoll_ev = float(data[47][9])
TMO_VMT_hvtoll_ea = float(data[43][10])
TMO_VMT_hvtoll_am = float(data[44][10])
TMO_VMT_hvtoll_md = float(data[45][10])
TMO_VMT_hvtoll_pm = float(data[46][10])
TMO_VMT_hvtoll_ev = float(data[47][10])

TMO_nrdelay = float(data[58][0])
TMO_veh_fatal = float(data[61][1])
TMO_veh_inj = float(data[62][1])
TMO_veh_pdo = float(data[63][1])
TMO_ped_fatal = float(data[64][1])
TMO_ped_inj = float(data[65][1])
TMO_bk_fatal = float(data[66][1])
TMO_bk_inj = float(data[67][1])

TMO_ROG = float(data[70][1])
TMO_S_NOx = float(data[71][1])
TMO_SO2 = float(data[72][1])
TMO_W_NOx = float(data[73][1])
TMO_CO2 = float(data[74][1])
TMO_D_PM_fine = float(data[75][1])
TMO_G_PM_fine = float(data[76][1])
TMO_D_PM_coarse = float(data[77][1])
TMO_butadiene = float(data[78][1])
TMO_benzene = float(data[79][1])
TMO_acetaldehyde = float(data[80][1])
TMO_formaldehyde = float(data[81][1])
TMO_exh_TOG = float(data[82][1])


# CALCULATE DAILY VALUES FOR BENEFIT-COST - potential errors noted in Excel file

tt_sov = (TMO_VHT_da_ea+TMO_VHT_da_am+TMO_VHT_da_md+TMO_VHT_da_pm+TMO_VHT_da_ev+
          TMO_VHT_datoll_ea+TMO_VHT_datoll_am+TMO_VHT_datoll_md+TMO_VHT_datoll_pm+
          TMO_VHT_datoll_ev)
tt_hov2 = 2*(TMO_VHT_sr2_ea+TMO_VHT_sr2_am+TMO_VHT_sr2_md+TMO_VHT_sr2_pm+
             TMO_VHT_sr2_ev+TMO_VHT_sr2toll_ea+TMO_VHT_sr2toll_am+
             TMO_VHT_sr2toll_md+TMO_VHT_sr2toll_pm+TMO_VHT_sr2toll_ev)
tt_hov3 = 3.5*(TMO_VHT_sr3_ea+TMO_VHT_sr3_am+TMO_VHT_sr3_md+TMO_VHT_sr3_pm+
               TMO_VHT_sr3_ev+TMO_VHT_sr3toll_ea+TMO_VHT_sr3toll_am+
               TMO_VHT_sr3toll_md+TMO_VHT_sr3toll_pm+TMO_VHT_sr3toll_ev)
tt_truck = (TMO_VHT_sm_ea+TMO_VHT_sm_am+TMO_VHT_sm_md+TMO_VHT_sm_pm+TMO_VHT_sm_ev+
            TMO_VHT_hv_ea+TMO_VHT_hv_am+TMO_VHT_hv_md+TMO_VHT_hv_pm+TMO_VHT_hv_ev+
            TMO_VHT_smtoll_ea+TMO_VHT_smtoll_am+TMO_VHT_smtoll_md+TMO_VHT_smtoll_pm+
            TMO_VHT_smtoll_ev+TMO_VHT_hvtoll_ea+TMO_VHT_hvtoll_am+TMO_VHT_hvtoll_md+
            TMO_VHT_hvtoll_pm+TMO_VHT_hvtoll_ev)
nrdelay_auto = TMO_nrdelay*(TMO_VHT_da_ea+TMO_VHT_da_am+TMO_VHT_da_md+TMO_VHT_da_pm+
               TMO_VHT_da_ev+TMO_VHT_datoll_ea+TMO_VHT_datoll_am+TMO_VHT_datoll_md+
               TMO_VHT_datoll_pm+TMO_VHT_datoll_ev+TMO_VHT_sr2_ea+TMO_VHT_sr2_am+
               TMO_VHT_sr2_md+TMO_VHT_sr2_pm+TMO_VHT_sr2_ev+TMO_VHT_sr2toll_ea+
               TMO_VHT_sr2toll_am+TMO_VHT_sr2toll_md+TMO_VHT_sr2toll_pm+
               TMO_VHT_sr2toll_ev+TMO_VHT_sr3_ea+TMO_VHT_sr3_am+TMO_VHT_sr3_md+
               TMO_VHT_sr3_pm+TMO_VHT_sr3_ev+TMO_VHT_sr3toll_ea+TMO_VHT_sr3toll_am+
               TMO_VHT_sr3toll_md+TMO_VHT_sr3toll_pm+TMO_VHT_sr3toll_ev)/((TMO_VHT_da_ea+
               TMO_VHT_da_am+TMO_VHT_da_md+TMO_VHT_da_pm+TMO_VHT_da_ev+TMO_VHT_datoll_ea+
               TMO_VHT_datoll_am+TMO_VHT_datoll_md+TMO_VHT_datoll_pm+TMO_VHT_datoll_ev+
               TMO_VHT_sr2_ea+TMO_VHT_sr2_am+TMO_VHT_sr2_md+TMO_VHT_sr2_pm+
               TMO_VHT_sr2_ev+TMO_VHT_sr2toll_ea+TMO_VHT_sr2toll_am+TMO_VHT_sr2toll_md+
               TMO_VHT_sr2toll_pm+TMO_VHT_sr2toll_ev+TMO_VHT_sr3_ea+TMO_VHT_sr3_am+
               TMO_VHT_sr3_md+TMO_VHT_sr3_pm+TMO_VHT_sr3_ev+TMO_VHT_sr3toll_ea+
               TMO_VHT_sr3toll_am+TMO_VHT_sr3toll_md+TMO_VHT_sr3toll_pm+
               TMO_VHT_sr3toll_ev)+(TMO_VHT_sm_ea+TMO_VHT_sm_am+TMO_VHT_sm_md+
               TMO_VHT_sm_pm+TMO_VHT_sm_ev+TMO_VHT_hv_ea+TMO_VHT_hv_am+TMO_VHT_hv_md+
               TMO_VHT_hv_pm+TMO_VHT_hv_ev+TMO_VHT_smtoll_ea+TMO_VHT_smtoll_am+
               TMO_VHT_smtoll_md+TMO_VHT_smtoll_pm+TMO_VHT_smtoll_ev+
               TMO_VHT_hvtoll_ea+TMO_VHT_hvtoll_am+TMO_VHT_hvtoll_md+TMO_VHT_hvtoll_pm+
               TMO_VHT_hvtoll_ev))
nrdelay_truck = TMO_nrdelay*(TMO_VHT_sm_ea+TMO_VHT_sm_am+TMO_VHT_sm_md+TMO_VHT_sm_pm+
                TMO_VHT_sm_ev+TMO_VHT_hv_ea+TMO_VHT_hv_am+TMO_VHT_hv_md+TMO_VHT_hv_pm+
                TMO_VHT_hv_ev+TMO_VHT_smtoll_ea+TMO_VHT_smtoll_am+TMO_VHT_smtoll_md+
                TMO_VHT_smtoll_pm+TMO_VHT_smtoll_ev+TMO_VHT_hvtoll_ea+TMO_VHT_hvtoll_am+
                TMO_VHT_hvtoll_md+TMO_VHT_hvtoll_pm+TMO_VHT_hvtoll_ev)/((TMO_VHT_da_ea+
                TMO_VHT_da_am+TMO_VHT_da_md+TMO_VHT_da_pm+TMO_VHT_da_ev+
                TMO_VHT_datoll_ea+TMO_VHT_datoll_am+TMO_VHT_datoll_md+TMO_VHT_datoll_pm+
                TMO_VHT_datoll_ev+TMO_VHT_sr2_ea+TMO_VHT_sr2_am+TMO_VHT_sr2_md+
                TMO_VHT_sr2_pm+TMO_VHT_sr2_ev+TMO_VHT_sr2toll_ea+TMO_VHT_sr2toll_am+
                TMO_VHT_sr2toll_md+TMO_VHT_sr2toll_pm+TMO_VHT_sr2toll_ev+TMO_VHT_sr3_ea+
                TMO_VHT_sr3_am+TMO_VHT_sr3_md+TMO_VHT_sr3_pm+TMO_VHT_sr3_ev+
                TMO_VHT_sr3toll_ea+TMO_VHT_sr3toll_am+TMO_VHT_sr3toll_md+
                TMO_VHT_sr3toll_pm+TMO_VHT_sr3toll_ev)+(TMO_VHT_sm_ea+TMO_VHT_sm_am+
                TMO_VHT_sm_md+TMO_VHT_sm_pm+TMO_VHT_sm_ev+TMO_VHT_hv_ea+TMO_VHT_hv_am+
                TMO_VHT_hv_md+TMO_VHT_hv_pm+TMO_VHT_hv_ev+TMO_VHT_smtoll_ea+
                TMO_VHT_smtoll_am+TMO_VHT_smtoll_md+TMO_VHT_smtoll_pm+TMO_VHT_smtoll_ev+
                TMO_VHT_hvtoll_ea+TMO_VHT_hvtoll_am+TMO_VHT_hvtoll_md+TMO_VHT_hvtoll_pm+
                TMO_VHT_hvtoll_ev))
tt_ivtt_com = (TMO_ivtt_wlk_com_wlk+TMO_ivtt_drv_com_wlk+TMO_ivtt_wlk_com_drv)
tt_ivtt_hvy = (TMO_ivtt_wlk_hvy_wlk+TMO_ivtt_drv_hvy_wlk+TMO_ivtt_wlk_hvy_drv)
tt_ivtt_exp = (TMO_ivtt_wlk_exp_wlk+TMO_ivtt_drv_exp_wlk+TMO_ivtt_wlk_exp_drv)
tt_ivtt_lrf = (TMO_ivtt_wlk_lrf_wlk+TMO_ivtt_drv_lrf_wlk+TMO_ivtt_wlk_lrf_drv)
tt_ivtt_loc = (TMO_ivtt_wlk_loc_wlk+TMO_ivtt_drv_loc_wlk+TMO_ivtt_wlk_loc_drv)
tt_ovtt_wk = (TMO_wlkaceg_wlk_com_wlk+TMO_wlkaceg_drv_com_wlk+TMO_wlkaceg_wlk_com_drv+
              TMO_wlkaceg_wlk_hvy_wlk+TMO_wlkaceg_drv_hvy_wlk+TMO_wlkaceg_wlk_hvy_drv+
              TMO_wlkaceg_wlk_exp_wlk+TMO_wlkaceg_drv_exp_wlk+TMO_wlkaceg_wlk_exp_drv+
              TMO_wlkaceg_wlk_lrf_wlk+TMO_wlkaceg_drv_lrf_wlk+TMO_wlkaceg_wlk_lrf_drv+
              TMO_wlkaceg_wlk_loc_wlk+TMO_wlkaceg_drv_loc_wlk+TMO_wlkaceg_wlk_loc_drv+
              TMO_auxwlk_wlk_com_wlk+TMO_auxwlk_drv_com_wlk+TMO_auxwlk_wlk_com_drv+
              TMO_auxwlk_wlk_hvy_wlk+TMO_auxwlk_drv_hvy_wlk+TMO_auxwlk_wlk_hvy_drv+
              TMO_auxwlk_wlk_exp_wlk+TMO_auxwlk_drv_exp_wlk+TMO_auxwlk_wlk_exp_drv+
              TMO_auxwlk_wlk_lrf_wlk+TMO_auxwlk_drv_lrf_wlk+TMO_auxwlk_wlk_lrf_drv+
              TMO_auxwlk_wlk_loc_wlk+TMO_auxwlk_drv_loc_wlk+TMO_auxwlk_wlk_loc_drv)
tt_ovtt_dr = (TMO_draceg_wlk_com_wlk+TMO_draceg_drv_com_wlk+TMO_draceg_wlk_com_drv+
              TMO_draceg_wlk_hvy_wlk+TMO_draceg_drv_hvy_wlk+TMO_draceg_wlk_hvy_drv+
              TMO_draceg_wlk_exp_wlk+TMO_draceg_drv_exp_wlk+TMO_draceg_wlk_exp_drv+
              TMO_draceg_wlk_lrf_wlk+TMO_draceg_drv_lrf_wlk+TMO_draceg_wlk_lrf_drv+
              TMO_draceg_wlk_loc_wlk+TMO_draceg_drv_loc_wlk+TMO_draceg_wlk_loc_drv)
tt_ovtt_wait = (TMO_iwait_wlk_com_wlk+TMO_iwait_drv_com_wlk+TMO_iwait_wlk_com_drv+
                TMO_iwait_wlk_hvy_wlk+TMO_iwait_drv_hvy_wlk+TMO_iwait_wlk_hvy_drv+
                TMO_iwait_wlk_exp_wlk+TMO_iwait_drv_exp_wlk+TMO_iwait_wlk_exp_drv+
                TMO_iwait_wlk_lrf_wlk+TMO_iwait_drv_lrf_wlk+TMO_iwait_wlk_lrf_drv+
                TMO_iwait_wlk_loc_wlk+TMO_iwait_drv_loc_wlk+TMO_iwait_wlk_loc_drv+
                TMO_xfer_wlk_com_wlk+TMO_xfer_drv_com_wlk+TMO_xfer_wlk_com_drv+
                TMO_xfer_wlk_hvy_wlk+TMO_xfer_drv_hvy_wlk+TMO_xfer_wlk_hvy_drv+
                TMO_xfer_wlk_exp_wlk+TMO_xfer_drv_exp_wlk+TMO_xfer_wlk_exp_drv+
                TMO_xfer_wlk_lrf_wlk+TMO_xfer_drv_lrf_wlk+TMO_xfer_wlk_lrf_drv+
                TMO_xfer_wlk_loc_wlk+TMO_xfer_drv_loc_wlk+TMO_xfer_wlk_loc_drv)
autrips_per = (TMO_autrips_da+TMO_autrips_datoll+TMO_autrips_sr2+TMO_autrips_sr2toll+
               TMO_autrips_sr3+TMO_autrips_sr3toll)
autrips_veh = (TMO_autrips_da+TMO_autrips_datoll)+(TMO_autrips_sr2+
               TMO_autrips_sr2toll)/2+(TMO_autrips_sr3+TMO_autrips_sr3toll)/3.5
tt_wk = (TMO_wktrips*TMO_wkavgtime)/60
tt_bk = (TMO_bktrips*TMO_bkavgtime)/60
vmt_auto = sum([TMO_VMT_da_ea,TMO_VMT_da_am,TMO_VMT_da_md,TMO_VMT_da_pm,TMO_VMT_da_ev,
                TMO_VMT_datoll_ea,TMO_VMT_datoll_am,TMO_VMT_datoll_md,TMO_VMT_datoll_pm,
                TMO_VMT_datoll_ev,TMO_VMT_sr2_ea,TMO_VMT_sr2_am,TMO_VMT_sr2_md,
                TMO_VMT_sr2_pm,TMO_VMT_sr2_ev,TMO_VMT_sr2toll_ea,TMO_VMT_sr2toll_am,
                TMO_VMT_sr2toll_md,TMO_VMT_sr2toll_pm,TMO_VMT_sr2toll_ev,TMO_VMT_sr3_ea,
                TMO_VMT_sr3_am,TMO_VMT_sr3_md,TMO_VMT_sr3_pm,TMO_VMT_sr3_ev,
                TMO_VMT_sr3toll_ea,TMO_VMT_sr3toll_am,TMO_VMT_sr3toll_md,
                TMO_VMT_sr3toll_pm,TMO_VMT_sr3toll_ev])
vmt_truck = sum([TMO_VMT_sm_ea,TMO_VMT_sm_am,TMO_VMT_sm_md,TMO_VMT_sm_pm,TMO_VMT_sm_ev,
                 TMO_VMT_hv_ea,TMO_VMT_hv_am,TMO_VMT_hv_md,TMO_VMT_hv_pm,TMO_VMT_hv_ev,
                 TMO_VMT_smtoll_ea,TMO_VMT_smtoll_am,TMO_VMT_smtoll_md,TMO_VMT_smtoll_pm,
                 TMO_VMT_smtoll_ev,TMO_VMT_hvtoll_ea,TMO_VMT_hvtoll_am,TMO_VMT_hvtoll_md,
                 TMO_VMT_hvtoll_pm,TMO_VMT_hvtoll_ev])
d_pm_fine = TMO_G_PM_fine*1.10231+(sum([TMO_VMT_da_ea,TMO_VMT_da_am,TMO_VMT_da_md,
                                        TMO_VMT_da_pm,TMO_VMT_da_ev,TMO_VMT_datoll_ea,
                                        TMO_VMT_datoll_am,TMO_VMT_datoll_md,
                                        TMO_VMT_datoll_pm,TMO_VMT_datoll_ev,
                                        TMO_VMT_sr2_ea,TMO_VMT_sr2_am,TMO_VMT_sr2_md,
                                        TMO_VMT_sr2_pm,TMO_VMT_sr2_ev,
                                        TMO_VMT_sr2toll_ea,TMO_VMT_sr2toll_am,
                                        TMO_VMT_sr2toll_md,TMO_VMT_sr2toll_pm,
                                        TMO_VMT_sr2toll_ev,TMO_VMT_sr3_ea,
                                        TMO_VMT_sr3_am,TMO_VMT_sr3_md,TMO_VMT_sr3_pm,
                                        TMO_VMT_sr3_ev,TMO_VMT_sr3toll_ea,
                                        TMO_VMT_sr3toll_am,TMO_VMT_sr3toll_md,
                                        TMO_VMT_sr3toll_pm,TMO_VMT_sr3toll_ev])*
                                        (0.007+0.01891)*0.00000110231131)
g_pm_fine = TMO_D_PM_fine*1.10231+(sum([TMO_VMT_sm_ea,TMO_VMT_sm_am,TMO_VMT_sm_md,
                                        TMO_VMT_sm_pm,TMO_VMT_sm_ev,TMO_VMT_hv_ea,
                                        TMO_VMT_hv_am,TMO_VMT_hv_md,TMO_VMT_hv_pm,
                                        TMO_VMT_hv_ev,TMO_VMT_smtoll_ea,
                                        TMO_VMT_smtoll_am,TMO_VMT_smtoll_md,
                                        TMO_VMT_smtoll_pm,TMO_VMT_smtoll_ev,
                                        TMO_VMT_hvtoll_ea,TMO_VMT_hvtoll_am,
                                        TMO_VMT_hvtoll_md,TMO_VMT_hvtoll_pm,
                                        TMO_VMT_hvtoll_ev])*(0.007+0.01891)*0.00000110231131)
co2 = TMO_CO2
acetaldehyde = TMO_acetaldehyde*1.10231
benzene = TMO_benzene*1.10231
butadiene = TMO_butadiene*1.10231
formaldehyde = TMO_formaldehyde*1.10231
rog_other = (TMO_ROG-TMO_butadiene-TMO_benzene-TMO_acetaldehyde-TMO_formaldehyde)*1.10231
nox = TMO_W_NOx*1.10231
so2 = TMO_SO2*1.10231
fatal = sum([TMO_veh_fatal,TMO_ped_fatal,TMO_bk_fatal])
injury = sum([TMO_veh_inj,TMO_ped_inj,TMO_bk_inj])
pdo = TMO_veh_pdo

# INCORPORATE USER INPUT FOR KEY VARIABLES

mode = input_data[3][1]
park_per_sf = float(input_data[5][1])
park_per_sm = float(input_data[6][1])
park_per_scl = float(input_data[7][1])
park_per_ala = float(input_data[8][1])
park_per_cc = float(input_data[9][1])
park_per_sol = float(input_data[10][1])
park_per_nap = float(input_data[11][1])
park_per_son = float(input_data[12][1])
park_per_mrn = float(input_data[13][1])
if sum([park_per_sf, park_per_sm, park_per_scl, park_per_ala, park_per_cc,
        park_per_sol, park_per_nap, park_per_son, park_per_mrn])<>1:
            print('Error: parking values do not sum to 1.')

use_default = input_data[4][1]

if use_default == 'Y':
    ownership_fac = 1583
    pop_2040 = 9299150
else: 
    ownership_fac = float(input('Auto Ownership Factor: '))
    pop_2040 = float(input('2040 Population: '))

# CALCULATE REMAINING VALUES BASED ON USER INPUT
veh_ownership = autrips_veh*annualization/ownership_fac
active_time = ((TMO_wktrips*TMO_wkavgdist)/pop_2040/3*60+(TMO_bktrips*TMO_bkavgdist)/pop_2040/12*60+(TMO_wlkaceg_wlk_com_wlk+
                TMO_wlkaceg_drv_com_wlk+TMO_wlkaceg_wlk_com_drv+TMO_wlkaceg_wlk_hvy_wlk+
                TMO_wlkaceg_drv_hvy_wlk+TMO_wlkaceg_wlk_hvy_drv+TMO_wlkaceg_wlk_exp_wlk+
                TMO_wlkaceg_drv_exp_wlk+TMO_wlkaceg_wlk_exp_drv+TMO_wlkaceg_wlk_lrf_wlk+
                TMO_wlkaceg_drv_lrf_wlk+TMO_wlkaceg_wlk_lrf_drv+TMO_wlkaceg_wlk_loc_wlk+
                TMO_wlkaceg_drv_loc_wlk+TMO_wlkaceg_wlk_loc_drv+TMO_auxwlk_wlk_com_wlk+
                TMO_auxwlk_drv_com_wlk+TMO_auxwlk_wlk_com_drv+TMO_auxwlk_wlk_hvy_wlk+
                TMO_auxwlk_drv_hvy_wlk+TMO_auxwlk_wlk_hvy_drv+TMO_auxwlk_wlk_exp_wlk+
                TMO_auxwlk_drv_exp_wlk+TMO_auxwlk_wlk_exp_drv+TMO_auxwlk_wlk_lrf_wlk+
                TMO_auxwlk_drv_lrf_wlk+TMO_auxwlk_wlk_lrf_drv+TMO_auxwlk_wlk_loc_wlk+
                TMO_auxwlk_drv_loc_wlk+TMO_auxwlk_wlk_loc_drv)*60/pop_2040)
active_indv = active_time*0.62/30*pop_2040

tr_trips = (TMO_trtrips_wlk_com_wlk + TMO_trtrips_drv_com_wlk +
            TMO_trtrips_wlk_com_drv + TMO_trtrips_wlk_hvy_wlk +
            TMO_trtrips_drv_hvy_wlk + TMO_trtrips_wlk_hvy_drv +
            TMO_trtrips_wlk_exp_wlk + TMO_trtrips_drv_exp_wlk +
            TMO_trtrips_wlk_exp_drv + TMO_trtrips_wlk_lrf_wlk +
            TMO_trtrips_drv_lrf_wlk + TMO_trtrips_wlk_lrf_drv +
            TMO_trtrips_wlk_loc_wlk + TMO_trtrips_drv_loc_wlk +
            TMO_trtrips_wlk_loc_drv)

if mode == "com":
    ovtt_adjust = ((TMO_ovtt_wlk_com_wlk+TMO_ovtt_drv_com_wlk+TMO_ovtt_wlk_com_drv)/
                   (TMO_trtrips_wlk_com_wlk+TMO_trtrips_drv_com_wlk+TMO_trtrips_wlk_com_drv))
elif mode == "hvy":
    ovtt_adjust = ((TMO_ovtt_wlk_hvy_wlk+TMO_ovtt_drv_hvy_wlk+TMO_ovtt_wlk_hvy_drv)/
                   (TMO_trtrips_wlk_hvy_wlk+TMO_trtrips_drv_hvy_wlk+TMO_trtrips_wlk_hvy_drv))
elif mode == "exp":
    ovtt_adjust = ((TMO_ovtt_wlk_exp_wlk+TMO_ovtt_drv_exp_wlk+TMO_ovtt_wlk_exp_drv)/
                   (TMO_trtrips_wlk_exp_wlk+TMO_trtrips_drv_exp_wlk+TMO_trtrips_wlk_exp_drv))
elif mode == "lrf":
    ovtt_adjust = ((TMO_ovtt_wlk_lrf_wlk+TMO_ovtt_drv_lrf_wlk+TMO_ovtt_wlk_lrf_drv)/
                   (TMO_trtrips_wlk_lrf_wlk+TMO_trtrips_drv_lrf_wlk+TMO_trtrips_wlk_lrf_drv))
elif mode == "loc":
    ovtt_adjust = ((TMO_ovtt_wlk_loc_wlk+TMO_ovtt_drv_loc_wlk+TMO_ovtt_wlk_loc_drv)/
                   (TMO_trtrips_wlk_loc_wlk+TMO_trtrips_drv_loc_wlk+TMO_trtrips_wlk_loc_drv))
elif mode == "road":
    ovtt_adjust = sum([TMO_ovtt_wlk_com_wlk,TMO_ovtt_drv_com_wlk,TMO_ovtt_wlk_com_drv,
                       TMO_ovtt_wlk_hvy_wlk,TMO_ovtt_drv_hvy_wlk,TMO_ovtt_wlk_hvy_drv,
                       TMO_ovtt_wlk_exp_wlk,TMO_ovtt_drv_exp_wlk,TMO_ovtt_wlk_exp_drv,
                       TMO_ovtt_wlk_lrf_wlk,TMO_ovtt_drv_lrf_wlk,TMO_ovtt_wlk_lrf_drv,
                       TMO_ovtt_wlk_loc_wlk,TMO_ovtt_drv_loc_wlk,TMO_ovtt_wlk_loc_drv]
                       )/sum([TMO_trtrips_wlk_com_wlk,TMO_trtrips_drv_com_wlk,
                              TMO_trtrips_wlk_com_drv,TMO_trtrips_wlk_hvy_wlk,
                              TMO_trtrips_drv_hvy_wlk,TMO_trtrips_wlk_hvy_drv,
                              TMO_trtrips_wlk_exp_wlk,TMO_trtrips_drv_exp_wlk,
                              TMO_trtrips_wlk_exp_drv,TMO_trtrips_wlk_lrf_wlk,
                              TMO_trtrips_drv_lrf_wlk,TMO_trtrips_wlk_lrf_drv,
                              TMO_trtrips_wlk_loc_wlk,TMO_trtrips_drv_loc_wlk,
                              TMO_trtrips_wlk_loc_drv])
else:
    print('Error: invalid mode input')


# WRITE PROJECT DAILY OUTPUTS TO CSV
csv_output = [tt_sov, tt_hov2, tt_hov3, tt_truck, nrdelay_auto, nrdelay_truck, # 0-5
              tt_ivtt_com, tt_ivtt_hvy, tt_ivtt_exp, tt_ivtt_lrf, tt_ivtt_loc, # 6-10
              tt_ovtt_wk, tt_ovtt_dr, tt_ovtt_wait, autrips_per, autrips_veh,  # 11-15
              tt_wk, tt_bk, vmt_auto, vmt_truck, d_pm_fine, g_pm_fine, co2,    # 16-22
              acetaldehyde, benzene, butadiene, formaldehyde, rog_other, nox,  # 23-28
              so2, fatal, injury, pdo, park_per_sf, park_per_sm, park_per_scl, # 29-35
              park_per_ala, park_per_cc, park_per_sol, park_per_nap,           # 36-39
              park_per_son, park_per_mrn, ownership_fac, pop_2040, veh_ownership, # 40-44
              active_time, active_indv, ovtt_adjust, autrips_per]              # 45-48
                       
csv_file_name = project_id + '_step1output.csv'
f = open(csv_file_name,'wt')
writer = csv.writer(f)
writer.writerow(csv_output)
f.close()

exit