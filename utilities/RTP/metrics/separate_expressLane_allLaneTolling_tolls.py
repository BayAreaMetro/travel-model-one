import os
import pandas as pd
import geopandas as gpd



# network INPUT which as A, B, TOLLCLASS, and USE
dbp_network_input_v18 = gpd.read_file(r'M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\Networks\BlueprintNetworks_v18\net_2050_Blueprint\shapefile\network_links.shp')
print(dbp_network_input_v18.shape[0])
print(dbp_network_input_v18[['A', 'B']].drop_duplicates().shape[0])


# network OUTPUT
for directory in ['2023_TM160_IPA_55', '2035_TM160_DBP_Plan_08b', '2050_TM160_DBP_Plan_08b']:

    # network OUTPUT with has vol data
    if directory == '2023_TM160_IPA_55':
        loaded_hwy_file = r'M:\Application\Model One\RTP2025\IncrementalProgress\{}\OUTPUT\shapefile\network_links.shp'.format(directory)
    else:
        loaded_hwy_file = r'M:\Application\Model One\RTP2025\Blueprint\{}\OUTPUT\shapefile\network_links.shp'.format(directory)
    
    print(loaded_hwy_file)
    dbp_network_output = gpd.read_file(loaded_hwy_file)
    print(dbp_network_output.shape[0])
    print(dbp_network_output.head())

    # merge into the 'USE' column to network output data
    dbp_network_output = dbp_network_output.merge(dbp_network_input_v18[['A', 'B', 'USE']], on=['A', 'B'], how='left')
    print(dbp_network_output.shape[0])

    # construct FAC_INDEX from TOLLCLASS and USE - this is mainly for QAQC
    dbp_network_output['FAC_INDEX'] = 0
    dbp_network_output.loc[dbp_network_output['TOLLCLASS'] > 0, 'FAC_INDEX'] = dbp_network_output['TOLLCLASS'] * 1000 + dbp_network_output['USE']
    print(dbp_network_output['FAC_INDEX'].nunique())
    print(dbp_network_output['FAC_INDEX'].unique())

    # label express lane versus all-lane tolling
    dbp_network_output['TOLL_CAT'] = ''
    dbp_network_output.loc[dbp_network_output['TOLLCLASS'] > 990000, 'TOLL_CAT'] = 'all-lane-tolling'
    dbp_network_output.loc[(dbp_network_output['TOLLCLASS'] <= 8) & (dbp_network_output['TOLLCLASS'] > 0), 'TOLL_CAT'] = 'bridge toll'
    dbp_network_output.loc[(dbp_network_output['TOLLCLASS'] > 8) & (dbp_network_output['TOLLCLASS'] < 990000), 'TOLL_CAT'] = 'non all-lane-tolling'
    print(dbp_network_output[['TOLL_CAT', 'TOLLCLASS']].drop_duplicates())

    # drop bridge toll links - this analysis only focuses on value tolls
    dbp_network_output_nonBridge = dbp_network_output.loc[dbp_network_output['TOLLCLASS'] > 8]

    # verify that for non-bridge toll links, VSM, SML, MED have the same toll value - this is because the loaded hwy data already combines the vols from VSM, SML, MED. 
    print(dbp_network_output_nonBridge.loc[(dbp_network_output_nonBridge['TOLLAM_VSM'] != dbp_network_output_nonBridge['TOLLAM_SML']) | (dbp_network_output_nonBridge['TOLLAM_VSM'] != dbp_network_output_nonBridge['TOLLAM_MED'])])
    print(dbp_network_output_nonBridge.loc[(dbp_network_output_nonBridge['TOLLMD_VSM'] != dbp_network_output_nonBridge['TOLLMD_SML']) | (dbp_network_output_nonBridge['TOLLMD_VSM'] != dbp_network_output_nonBridge['TOLLMD_MED'])])
    print(dbp_network_output_nonBridge.loc[(dbp_network_output_nonBridge['TOLLPM_VSM'] != dbp_network_output_nonBridge['TOLLPM_SML']) | (dbp_network_output_nonBridge['TOLLPM_VSM'] != dbp_network_output_nonBridge['TOLLPM_MED'])])

    # calculation total tolls
    # for VOL of SM and SMT, use TOLL_VSM because it equals TOLL_SML and TOLL_MED
    """
    # V1 - only count volumns with 'T'
    dbp_network_output_nonBridge['TOT_tolls_EA'] = \
        dbp_network_output_nonBridge['VOLEA_DAT'] * dbp_network_output_nonBridge['TOLLEA_DA'] + \
        dbp_network_output_nonBridge['VOLEA_S2T'] * dbp_network_output_nonBridge['TOLLEA_S2'] + \
        dbp_network_output_nonBridge['VOLEA_S3T'] * dbp_network_output_nonBridge['TOLLEA_S3'] + \
        dbp_network_output_nonBridge['VOLEA_SMT'] * dbp_network_output_nonBridge['TOLLEA_VSM'] + \
        dbp_network_output_nonBridge['VOLEA_HVT'] * dbp_network_output_nonBridge['TOLLEA_LRG']
    
    dbp_network_output_nonBridge['TOT_tolls_AM'] = \
        dbp_network_output_nonBridge['VOLAM_DAT'] * dbp_network_output_nonBridge['TOLLAM_DA'] + \
        dbp_network_output_nonBridge['VOLAM_S2T'] * dbp_network_output_nonBridge['TOLLAM_S2'] + \
        dbp_network_output_nonBridge['VOLAM_S3T'] * dbp_network_output_nonBridge['TOLLAM_S3'] + \
        dbp_network_output_nonBridge['VOLAM_SMT'] * dbp_network_output_nonBridge['TOLLAM_VSM'] + \
        dbp_network_output_nonBridge['VOLAM_HVT'] * dbp_network_output_nonBridge['TOLLAM_LRG']

    dbp_network_output_nonBridge['TOT_tolls_MD'] = \
        dbp_network_output_nonBridge['VOLMD_DAT']* dbp_network_output_nonBridge['TOLLMD_DA'] + \
        dbp_network_output_nonBridge['VOLMD_S2T'] * dbp_network_output_nonBridge['TOLLMD_S2'] + \
        dbp_network_output_nonBridge['VOLMD_S3T'] * dbp_network_output_nonBridge['TOLLMD_S3'] + \
        dbp_network_output_nonBridge['VOLMD_SMT'] * dbp_network_output_nonBridge['TOLLMD_VSM'] + \
        dbp_network_output_nonBridge['VOLMD_HVT'] * dbp_network_output_nonBridge['TOLLMD_LRG']

    dbp_network_output_nonBridge['TOT_tolls_PM'] = \
        dbp_network_output_nonBridge['VOLPM_DAT'] * dbp_network_output_nonBridge['TOLLPM_DA'] + \
        dbp_network_output_nonBridge['VOLPM_S2T'] * dbp_network_output_nonBridge['TOLLPM_S2'] + \
        dbp_network_output_nonBridge['VOLPM_S3T'] * dbp_network_output_nonBridge['TOLLPM_S3'] + \
        dbp_network_output_nonBridge['VOLPM_SMT'] * dbp_network_output_nonBridge['TOLLPM_VSM'] + \
        dbp_network_output_nonBridge['VOLPM_HVT'] * dbp_network_output_nonBridge['TOLLPM_LRG']

    dbp_network_output_nonBridge['TOT_tolls_EV'] = \
        dbp_network_output_nonBridge['VOLEV_DAT'] * dbp_network_output_nonBridge['TOLLEV_DA'] + \
        dbp_network_output_nonBridge['VOLEV_S2T'] * dbp_network_output_nonBridge['TOLLEV_S2'] + \
        dbp_network_output_nonBridge['VOLEV_S3T'] * dbp_network_output_nonBridge['TOLLEV_S3'] + \
        dbp_network_output_nonBridge['VOLEV_SMT'] * dbp_network_output_nonBridge['TOLLEV_VSM'] + \
        dbp_network_output_nonBridge['VOLEV_HVT'] * dbp_network_output_nonBridge['TOLLEV_LRG']

    """
    # V2 - count everything
    dbp_network_output_nonBridge['TOT_tolls_EA'] = \
        dbp_network_output_nonBridge[['VOLEA_DA', 'VOLEA_DAT', 'VOLEA_DAAV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLEA_DA'] + \
        dbp_network_output_nonBridge[['VOLEA_S2', 'VOLEA_S2T', 'VOLEA_S2AV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLEA_S2'] + \
        dbp_network_output_nonBridge[['VOLEA_S3', 'VOLEA_S3T', 'VOLEA_S3AV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLEA_S3'] + \
        dbp_network_output_nonBridge[['VOLEA_SM', 'VOLEA_SMT']].sum(axis=1) * dbp_network_output_nonBridge['TOLLEA_VSM'] + \
        dbp_network_output_nonBridge[['VOLEA_HV', 'VOLEA_HVT']].sum(axis=1) * dbp_network_output_nonBridge['TOLLEA_LRG']
    
    dbp_network_output_nonBridge['TOT_tolls_AM'] = \
        dbp_network_output_nonBridge[['VOLAM_DA', 'VOLAM_DAT', 'VOLAM_DAAV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLAM_DA'] + \
        dbp_network_output_nonBridge[['VOLAM_S2', 'VOLAM_S2T', 'VOLAM_S2AV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLAM_S2'] + \
        dbp_network_output_nonBridge[['VOLAM_S3', 'VOLAM_S3T', 'VOLAM_S3AV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLAM_S3'] + \
        dbp_network_output_nonBridge[['VOLAM_SM', 'VOLAM_SMT']].sum(axis=1) * dbp_network_output_nonBridge['TOLLAM_VSM'] + \
        dbp_network_output_nonBridge[['VOLAM_HV', 'VOLAM_HVT']].sum(axis=1) * dbp_network_output_nonBridge['TOLLAM_LRG']

    dbp_network_output_nonBridge['TOT_tolls_MD'] = \
        dbp_network_output_nonBridge[['VOLMD_DA', 'VOLMD_DAT', 'VOLMD_DAAV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLMD_DA'] + \
        dbp_network_output_nonBridge[['VOLMD_S2', 'VOLMD_S2T', 'VOLMD_S2AV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLMD_S2'] + \
        dbp_network_output_nonBridge[['VOLMD_S3', 'VOLMD_S3T', 'VOLMD_S3AV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLMD_S3'] + \
        dbp_network_output_nonBridge[['VOLMD_SM', 'VOLMD_SMT']].sum(axis=1) * dbp_network_output_nonBridge['TOLLMD_VSM'] + \
        dbp_network_output_nonBridge[['VOLMD_HV', 'VOLMD_HVT']].sum(axis=1) * dbp_network_output_nonBridge['TOLLMD_LRG']

    dbp_network_output_nonBridge['TOT_tolls_PM'] = \
        dbp_network_output_nonBridge[['VOLPM_DA', 'VOLPM_DAT', 'VOLPM_DAAV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLPM_DA'] + \
        dbp_network_output_nonBridge[['VOLPM_S2', 'VOLPM_S2T', 'VOLPM_S2AV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLPM_S2'] + \
        dbp_network_output_nonBridge[['VOLPM_S3', 'VOLPM_S3T', 'VOLPM_S3AV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLPM_S3'] + \
        dbp_network_output_nonBridge[['VOLPM_SM', 'VOLPM_SMT']].sum(axis=1) * dbp_network_output_nonBridge['TOLLPM_VSM'] + \
        dbp_network_output_nonBridge[['VOLPM_HV', 'VOLPM_HVT']].sum(axis=1) * dbp_network_output_nonBridge['TOLLPM_LRG']
    
    dbp_network_output_nonBridge['TOT_tolls_EV'] = \
        dbp_network_output_nonBridge[['VOLEV_DA', 'VOLEV_DAT', 'VOLEV_DAAV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLEV_DA'] + \
        dbp_network_output_nonBridge[['VOLEV_S2', 'VOLEV_S2T', 'VOLEV_S2AV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLEV_S2'] + \
        dbp_network_output_nonBridge[['VOLEV_S3', 'VOLEV_S3T', 'VOLEV_S3AV']].sum(axis=1) * dbp_network_output_nonBridge['TOLLEV_S3'] + \
        dbp_network_output_nonBridge[['VOLEV_SM', 'VOLEV_SMT']].sum(axis=1) * dbp_network_output_nonBridge['TOLLEV_VSM'] + \
        dbp_network_output_nonBridge[['VOLEV_HV', 'VOLEV_HVT']].sum(axis=1) * dbp_network_output_nonBridge['TOLLEV_LRG']
    
    # sum up to daily toll 
    dbp_network_output_nonBridge['TOT_tolls_24hr'] = dbp_network_output_nonBridge[[
        'TOT_tolls_EA', 'TOT_tolls_AM', 'TOT_tolls_MD', 'TOT_tolls_PM', 'TOT_tolls_EV']].sum(axis=1)

    # tally by toll class category
    toll_sum_df = dbp_network_output_nonBridge.groupby(['TOLL_CAT'])[
        'TOT_tolls_EA', 'TOT_tolls_AM', 'TOT_tolls_MD', 'TOT_tolls_PM', 'TOT_tolls_EV', 'TOT_tolls_24hr'].sum()
    print(toll_sum_df)
    # sum total value tolls
    toll_sum_df.loc['total'] = toll_sum_df.sum(axis=0)
    toll_sum_df.reset_index(inplace=True)
    print(toll_sum_df)

    for i in ['TOT_tolls_EA', 'TOT_tolls_AM', 'TOT_tolls_MD', 'TOT_tolls_PM', 'TOT_tolls_EV', 'TOT_tolls_24hr']:
        # convert to 2000 dollar
        toll_sum_df[i] = 0.01 * toll_sum_df[i]

    # add scen tag
    toll_sum_df['scen'] = directory
    print(toll_sum_df)

    toll_sum_df.to_csv(r'C:\Users\ywang\Box\Plan Bay Area 2050+\Needs & Revenues\Transportation\travel model output\value_tolls_sum_{}_V2.csv'.format(directory), index=False)
    
