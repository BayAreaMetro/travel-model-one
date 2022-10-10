"""
    Usage: python zone_seq_disseminator.py base_dir 

    where base_dir is the directory in which the model runs (directory with INPUTS, hwy, etc.)

    This script builds all of the CTRAMP files that use zone numbers in them. It is necessary to
    script this because the zone numbers that CTRAMP uses must be sequential and my change with
    any given model run (primarily because TAPs may change). See zone_seq_net_build.job for more
    details about this process and its necessity.
    
    This script first reads in the zone sequence correspondence, and builds mappings from/to the
    (CUBE) network zone numbers to the (CTRAMP) sequential zone numbers. This file is:
   
        base_dir\hwy\mtc_final_network_zone_seq.csv
        
    Then this script builds a number of output files, replacing the existing one, only with updated/added
    sequential numbers:
    
        base_dir\landuse\taz_data.csv - the taz data file; the sequential numbers are listed under TAZ,
            and the original zone numbers under TAZ_ORIGINAL
        base_dir\landuse\maz_data.csv - the maz data file; the sequential numbers are listed under MAZ,
            and the original zone numbers under MAZ_ORIGINAL
        base_dir\CTRAMP\model\ParkLocationAlts.csv - park location alternatives; basically a list of
            mazs built from maz_data.csv
        base_dir\CTRAMP\model\DestinationChoiceAlternatives.csv - destination choice alternatives; 
            basically a list of mazs and corresponding tazs built from maz_data.csv
        base_dir\CTRAMP\model\SoaTazDistAlternatives.csv - taz alternatives; basically a list of tazs
        base_dir\CTRAMP\model\ParkLocationSampleAlts.csv - park location sample alts; basically a list of mazs
        
    crf 11/2013

    jmh 2022 06: needs final TAZ data, on hold for now.
"""
import collections, sys, os
import pandas

def map_data(filename, sequence_mapping, mapping_dict):
    """ This function opens the given file joins it with the given sequence_mapping DataFrame
    according to mapping_dict.  

    Arguments:
    `filename` is the file
    `mapping_dict` defines the column assignment, mapping the new column name to a dictionary with two
                   items: 'seqcol' should map to column name in `sequence_mapping`, and 'N_col' should
                   map to the column that joins with `N` in sequence_mapping.
    
    e.g. mapping_dict = {'TAZ':{'seqcol' :'TAZSEQ',
                                'N_col'  :'TAZ_ORIGINAL'}}

    Returns the resulting DataFrame (after writing it out again)
    """
    dframe                = pandas.read_csv(filename)
    dframe.reset_index(inplace=True)

    for mapkey, mapdef in mapping_dict.iteritems():
        # delete mapkey if it's already there
        if mapkey in list(dframe.columns.values): dframe.drop(mapkey, axis=1, inplace=True)

        # join with sequence mapping (e.g. join N,TAZSEQ on TAZ_ORIGINAL)
        dframe = pandas.merge(left=sequence_mapping[['N',mapdef['seqcol']]], right=dframe, how='right', 
                              left_on='N', right_on=mapdef['N_col'])

        # verify everything in the original dataset joined
        missing_vals = dframe.loc[ dframe[mapdef['seqcol']].isnull() ]
        # print(missing_vals)
        assert(len(missing_vals)==0)

        # drop N - it's redundant
        dframe.drop('N', axis=1, inplace=True)
        # rename sequence column
        dframe.rename(columns={mapdef['seqcol']:mapkey}, inplace=True)

    # write it
    dframe.to_csv(filename, index=False, float_format="%.9f")
    print "Wrote %s" % filename
    return dframe

if __name__ == '__main__':
    ### shhhh
    pandas.options.mode.chained_assignment = None  # default='warn'

    base_dir                = sys.argv[1]
    zone_seq_mapping_file   = os.path.join(base_dir,'hwy',      'complete_network_zone_seq.csv')
    taz_data_file           = os.path.join(base_dir,'landuse',  'taz_data.csv') # TAZ,TAZ_ORIGINAL,AVGTTS,DIST,PCTDETOUR,TERMINALTIME
    #maz_data_file           = os.path.join(base_dir,'landuse',  'maz_data.csv') # MAZ,TAZ,MAZ_ORIGINAL,TAZ_ORIGINAL,HH,POP,emp_self,emp_ag,emp_const_non_bldg_prod,emp_const_non_bldg_office,emp_utilities_prod,emp_utilities_office,emp_const_bldg_prod,emp_const_bldg_office,emp_mfg_prod,emp_mfg_office,emp_whsle_whs,emp_trans,emp_retail,emp_prof_bus_svcs,emp_prof_bus_svcs_bldg_maint,emp_pvt_ed_k12,emp_pvt_ed_post_k12_oth,emp_health,emp_personal_svcs_office,emp_amusement,emp_hotel,emp_restaurant_bar,emp_personal_svcs_retail,emp_religious,emp_pvt_hh,emp_state_local_gov_ent,emp_scrap_other,emp_fed_non_mil,emp_fed_mil,emp_state_local_gov_blue,emp_state_local_gov_white,emp_public_ed,emp_own_occ_dwell_mgmt,emp_fed_gov_accts,emp_st_lcl_gov_accts,emp_cap_accts,emp_total,collegeEnroll,otherCollegeEnroll,AdultSchEnrl,EnrollGradeKto8,EnrollGrade9to12,PrivateEnrollGradeKto8,ech_dist,hch_dist,parkarea,hstallsoth,hstallssam,hparkcost,numfreehrs,dstallsoth,dstallssam,dparkcost,mstallsoth,mstallssam,mparkcost,TotInt,DUDen,EmpDen,PopDen,RetEmpDen,IntDenBin,EmpDenBin,DuDenBin,ACRES,beachAcres,mall_flag
    
    # the following isn't needed because it is dealt with in a different script
    #tap_data_file = os.path.join(base_dir,'trn/tap_data.csv') # tap,tap_original,lotid,taz,capacity
    #model_files_dir         = os.path.join(base_dir,'CTRAMP', 'model')
    
    #park_location_alts_file = os.path.join(model_files_dir,'ParkLocationAlts.csv') # a,mgra,parkarea
    #dc_alts_file            = os.path.join(model_files_dir,'DestinationChoiceAlternatives.csv')  # a,mgra,dest (a,mgra,taz)
    #soa_dist_alts_file      = os.path.join(model_files_dir,'SoaTazDistAlternatives.csv')  # a,dest (a,taz)
    #parking_soa_alts_file   = os.path.join(model_files_dir,'ParkLocationSampleAlts.csv')  # a,mgra
    
    sequence_mapping        = pandas.read_csv(zone_seq_mapping_file)
    sequence_mapping.reset_index(inplace=True)
    
    ######### map TAZ_ORIGINAL to the actual TAZ
    taz_data = map_data(taz_data_file, sequence_mapping, {'TAZ':{'seqcol':'TAZSEQ','N_col':'TAZ_ORIGINAL'}})
    
    ######### map TAZ_ORIGINAL to the actual TAZ and MAZ_ORIGINAL to MAZ
    mapping_dict = collections.OrderedDict()
    mapping_dict['TAZ'] = {'seqcol':'TAZSEQ','N_col':'TAZ_ORIGINAL'}
    #mapping_dict['MAZ'] = {'seqcol':'MAZSEQ','N_col':'MAZ_ORIGINAL'}
    #maz_data = map_data(maz_data_file, sequence_mapping,mapping_dict)
    
    ######### parkarea ?
    #parkarea = maz_data[['MAZ','parkarea']]
    #parkarea.sort_values(['MAZ'], inplace=True)
    #parkarea.reset_index(drop=True, inplace=True)
    #parkarea.loc[:,'a'] = range(1, parkarea.shape[0] + 1) # isn't this pointless?  MAZ is a consecutive sequence already
   # parkarea.rename(columns={'MAZ':'mgra'}, inplace=True)
    #parkarea = parkarea[['a','mgra','parkarea']]
    #parkarea.to_csv(park_location_alts_file, index=False)
    #print "Wrote %s" % park_location_alts_file

    ######### dc alternatives ?
    #dcalts = maz_data[['MAZ','TAZ']]
    #dcalts.sort_values(['MAZ','TAZ'], inplace=True)
    #dcalts.reset_index(drop=True, inplace=True)
    #dcalts.loc[:,'a'] = range(1, dcalts.shape[0] + 1) # isn't this pointless?  MAZ is a consecutive sequence already
    #dcalts.rename(columns={'MAZ':'mgra', 'TAZ':'dest'}, inplace=True)
    #dcalts = dcalts[['a','mgra','dest']]
    #dcalts.to_csv(dc_alts_file, index=False)
    #print "Wrote %s" % dc_alts_file
    
    ######### these seem truly pointless
    #dcalts.drop('dest', axis=1, inplace=True)
    #dcalts.to_csv(parking_soa_alts_file, index=False)
    #print "Wrote %s" % parking_soa_alts_file

    #soa_dist_alts = taz_data[['TAZ']]
    #soa_dist_alts.loc[:,'a'] = range(1, soa_dist_alts.shape[0] + 1) # ???
    #soa_dist_alts.rename(columns={'TAZ':'dest'}, inplace=True)
    #soa_dist_alts = soa_dist_alts[['a','dest']]
    #soa_dist_alts.to_csv(soa_dist_alts_file, index=False)
    #print "Wrote %s" % soa_dist_alts_file