DESCRIPTION = """

  Copies model run result files to M drive if they are more recent.
  Verifies that they are more recent.
  Backs up original xlsx file.


  Run this in the directory in M with all the model directories (destinations)
  e.g. M:\Application\Model One\RTP2017\Project Performance Assessment\Projects\_Complete


  Files copied:
  accessibilities/
    DestinationChoiceSizeTerms.csv_INDIVIDUAL_NON_MANDATORY.csv
    DestinationChoiceSizeTerms.csv_MANDATORY.csv
    mandatoryAccessibilities.csv
    nonMandatoryAccessibilities.csv
  metrics/
    vmt_vht_metrics.csv
    BC_*.xlsx

"""
import argparse, collections, datetime, glob, os, shutil, sys, time

MODEL_MACHINES_TO_MAPPED_DRIVES = {
    "model2-a" : r"D:\\",
    "model2-b" : r"A:\\",
    "model2-c" : r"E:\\",
    "model2-d" : r"I:\\"
}

# from M:\Application\Model One\RTP2017\Project Performance Assessment\Projects\_RerunLogsums_Jan20\ExistingRuns.xlsx
RUN_DIRS = [
	("2040_05_503",     "model2-b",    "Baseline 01 (2040_05_503)"),
	("2040_05_504",     "model2-c",    "Baseline 02 (2040_05_504)"),
	("2040_05_505",     "model2-b",    "Baseline 03 (2040_05_505)"),
	("2040_05_506",     "model2-b",    "Baseline 04 (2040_05_506)"),
	("2040_05_507",     "model2-c",    "Baseline 05 (2040_05_507)"),
	("2040_05_508",     "model2-a",    "Baseline 06 (2040_05_508)"),
	("2040_05_509",     "model2-a",    "Baseline 07 (2040_05_509)"),
	("2040_05_510",     "model2-d",    "Baseline 08 (2040_05_510)"),
	("2040_05_511",     "model2-a",    "Baseline 09 (2040_05_511)"),
	("2040_05_510_101", "model2-c",    "101_HOT"                  ),
	("2040_05_504_103", "model2-a",    "103_ECR"                  ),
	("2040_05_508_104", "model2-c",    "104_Geneva"               ),
	("2040_05_509_201", "model2-b",    "201_ACTExp"               ),
	("2040_05_511_202", "model2-a",    "202_Deco"                 ),
	("2040_05_504_203", "model2-a",    "203_Irvington"            ),
	("2040_05_504_204", "model2-a",    "204_Streetcar"            ),
	("2040_05_510_206", "model2-d",    "206_AC"                   ),
	("2040_05_509_207", "model2-b",    "207_SanPablo"             ),
	("2040_05_504_209", "model2-b",    "209_680_84"               ),
	("2040_05_509_210", "model2-d",    "210_580ICM"               ),
	("2040_05_509_211", "model2-b",    "211_Mission"              ),
	("2040_05_509_301", "model2-b",    "301_Geary_v2"             ),
	("2040_05_511_302", "model2-a",    "302_TI"                   ),
	("2040_05_506_303", "model2-a",    "303_BMS"                  ),
	("2040_05_510_304", "model2-a",    "304_Southeast"            ),
	("2040_05_510_307", "model2-b",    "307_dtx"                  ),
	("2040_05_511_308", "model2-b",    "308_SFexp"                ),
	("2040_05_511_311", "model2-d",    "311_TEP"                  ),
	("2040_05_509_401", "model2-d",    "401_Trilink"              ),
	("2040_05_510_402", "model2-b",    "402_ebart"                ),
	("2040_05_511_403", "model2-b",    "403_680bus"               ),
	("2040_05_509_404", "model2-c",    "404_SR4"                  ),
	("2040_05_509_406", "model2-c",    "406_680SR4"               ),
	("2040_05_509_407", "model2-c",    "407_SR4OI"                ),
	("2040_05_509_409", "model2-b",    "409_680SR4HOV"            ),
	("2040_05_511_410", "model2-b",    "410_CCFerries"            ),
	("2040_05_509_411", "model2-b",    "411_SR4OIPh2"             ),
	("2040_05_509_501", "model2-c",    "501_SVBX"                 ),
	("2040_05_509_503", "model2-d",    "503_152"                  ),
	("2040_05_509_504", "model2-d",    "504_StevensLRT"           ),
	("2040_05_509_505", "model2-d",    "505_Capitol"              ),
	("2040_05_507_506", "model2-b",    "506_elcamino"             ),
	("2040_05_511_507", "model2-c",    "507_Vasona"               ),
	("2040_05_511_508", "model2-c",    "508_SantaCruz"            ),
	("2040_05_509_510", "model2-d",    "510_Subway"               ),
	("2040_05_510_513", "model2-b",    "513_Bayshore"             ),
	("2040_05_511_514", "model2-c",    "514_Alviso"               ),
	("2040_05_509_515", "model2-c",    "515_Tasman"               ),
	("2040_05_509_516", "model2-d",    "516_SCExp"                ),
	("2040_05_509_517", "model2-d",    "517_StevensBRT"           ),
	("2040_05_509_518", "model2-d",    "518_ACE"                  ),
	("2040_05_509_519", "model2-b",    "519_Lawrence"             ),
	("2040_05_508_520", "model2-b",    "520_101880"               ),
	("2040_05_508_522", "model2-c",    "522_VTA"                  ),
	("2040_05_509_523", "model2-c",    "523_VTA"                  ),
	("2040_05_510_601", "model2-a",    "601_80_680_12"            ),
	("2040_05_509_602", "model2-c",    "602_SR12"                 ),
	("2040_05_509_604", "model2-d",    "604_SolanoExp"            ),
	("2040_05_509_605", "model2-c",    "605_Jepson"               ),
	("2040_05_509_801", "model2-d",    "801_GG"                   ),
	("2040_05_508_803", "model2-b",    "803_101580"               ),
	("2040_05_509_901", "model2-c",    "901_MSN"                  ),
	("2040_05_510_903", "model2-a",    "903_socobus"              ),
	("2040_05_510_905", "model2-a",    "905_SMART"                ),
	("2040_05_509_1001","model2-b",    "1001_Metro"               ),
	("2040_05_504_1002","model2-b",    "1002_BARTEVE"             ),
	("2040_05_504_1101","model2-b",    "1101_Electr"              ),
	("2040_05_507_1201","model2-c",    "1201_redwood"             ),
	("2040_05_509_1202","model2-b",    "1202_centralbay"          ),
	("2040_05_509_1203","model2-b",    "1203_northbay"            ),
	("2040_05_509_1204","model2-b",    "1204_berkeley"            ),
	("2040_05_509_1206","model2-d",    "1206_seaplane"            ),
	("2040_05_509_1301","model2-a",    "1301_CDI"                 ),
	("2040_05_509_1302","model2-b",    "1302_MTCExp"              ),
	("2040_05_509_1304","model2-b",    "1304_bike"                ),
	("2040_05_503_1401","model2-a",    "1401_LSRSGR_nofunding"    ),
	("2040_05_503_1402","model2-a",    "1402_LSRSGR_localfunding" ),
	("2040_05_503_1403","model2-b",    "1403_LSRSGR_preservePCI"  ),
	("2040_05_503_1405","model2-b",    "1405_LSRSGR_localfunding_"),
	("2040_05_503_1406","model2-b",    "1406_LSRSGR_preservePCI_w"),
	("2040_05_503_1501","model2-a",    "1501_Highway_nofunding"   ),
	("2040_05_503_1502","model2-a",    "1502_Highway_current"     ),
	("2040_05_503_1503","model2-b",    "1503_HighwaySGR_idealIRI" ),
	("2040_05_509_1601","model2-c",    "1601_BART_no_funding"     ),
	("2040_05_509_1602","model2-c",    "1602_BART_paoul"          ),
	("2040_05_509_1603","model2-b",    "1603_BART_current"        ),
	("2040_05_508_1604","model2-b",    "1604_Muni_rail_no_funding"),
	("2040_05_508_1605","model2-b",    "1605_Muni_rail_paoul"     ),
	("2040_05_508_1606","model2-b",    "1606_Muni_rail_current"   ),
	("2040_05_508_1607","model2-c",    "1607_Muni_bus_no_funding" ),
	("2040_05_508_1608","model2-c",    "1608_Muni_bus_paoul"      ),
	("2040_05_508_1609","model2-c",    "1609_Muni_bus_current"    ),
	("2040_05_509_1610","model2-d",    "1610_ACtransit_nofunding" ),
	("2040_05_509_1611","model2-d",    "1611_ACtransit_paoul"     ),
	("2040_05_509_1612","model2-b",    "1612_ACtransit_current"   ),
	("2040_05_509_1613","model2-b",    "1613_caltrain_no_funding" ),
	("2040_05_509_1614","model2-b",    "1614_caltrain_paoul"      ),
	("2040_05_509_1615","model2-b",    "1615_caltrain_current"    ),
	("2040_05_509_1616","model2-d",    "1616_ggbus_no_funding"    ),
	("2040_05_509_1617","model2-a",    "1617_ggbus_paoul"         ),
	("2040_05_509_1618","model2-a",    "1618_ggbus_current"       ),
	("2040_05_509_1619","model2-c",    "1619_sam_no_funding"      ),
	("2040_05_509_1620","model2-c",    "1620_sam_paoul"           ),
	("2040_05_509_1621","model2-c",    "1621_sam_current"         ),
	("2040_05_509_1622","model2-c",    "1622_small_no_funding"    ),
	("2040_05_509_1623","model2-c",    "1623_small_paoul"         ),
	("2040_05_509_1624","model2-d",    "1624_small_current"       ),
	("2040_05_509_1625","model2-d",    "1625_vtabus_no_funding"   ),
	("2040_05_509_1626","model2-d",    "1626_vtabus_paoul"        ),
	("2040_05_509_1627","model2-d",    "1627_vtabus_current"      ),
	("2040_05_509_1628","model2-a",    "1628_vtarail_no_funding"  ),
	("2040_05_509_1629","model2-a",    "1629_vtarail_paoul"       ),
	("2040_05_509_1630","model2-a",    "1630_vtarail_current"     )
]

# filename => glob?
COPY_FILES = collections.OrderedDict([
  (r"accessibilities\DestinationChoiceSizeTerms.csv_INDIVIDUAL_NON_MANDATORY.csv" ,False),
  (r"accessibilities\DestinationChoiceSizeTerms.csv_MANDATORY.csv"                ,False),
  (r"accessibilities\mandatoryAccessibilities.csv"                                ,False),
  (r"accessibilities\nonMandatoryAccessibilities.csv"                             ,False),
  (r"metrics\vmt_vht_metrics.csv"                                                 ,False),
  (r"metrics\BC_*.xlsx"                                                           ,True )
])

MOD_TIME_CHECK = time.strptime("01/20/16 16:00:00","%x %X")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dryrun', 
                        help="Print out what the script *would* do, but don't actually do it.",
                        action='store_true')
    args = parser.parse_args()

    if args.dryrun:
        print "Running DRYRUN"
    else:
        print "Not DRYRUN"

    for run_dir_tuple in RUN_DIRS:

        model_machine_dir = run_dir_tuple[0]
        model_machine     = run_dir_tuple[1]
        m_dir             = run_dir_tuple[2]

        print "%s Processing model run dir %s: %s => %s" % \
            (datetime.datetime.now().strftime("%x %X"), model_machine, model_machine_dir, m_dir)

        model_full_dir = os.path.join( MODEL_MACHINES_TO_MAPPED_DRIVES[model_machine], "Projects", model_machine_dir )

        for filename, is_glob in COPY_FILES.iteritems():
            model_file = os.path.join(model_full_dir, filename)

            if is_glob:
                model_glob_files = glob.glob(model_file)
                assert(len(model_glob_files)==1)
                model_file = model_glob_files[0]

            # assert that the file exists
            assert(os.path.exists(model_file))
            print "%s    Exists: %s" % (datetime.datetime.now().strftime("%x %X"), model_file)

            # assert that it was modified after 1/20/2016 4p
            create_time = time.localtime(os.path.getmtime(model_file))
            assert(create_time > MOD_TIME_CHECK)
            print "%s        is recent: %s" % (datetime.datetime.now().strftime("%x %X"), time.strftime("%x %X",create_time))

            # copy it over -- back up original
            new_filename = os.path.join(m_dir, "OUTPUT", os.path.split(filename)[0], os.path.split(model_file)[1])
            if os.path.exists(new_filename):
                bak_filename = new_filename
                if bak_filename[-5:-4] == '.':
                    bak_filename = bak_filename[:-5] + "_bak" + bak_filename[-5:]
                elif bak_filename[-4:-3] == '.':
                    bak_filename = bak_filename[:-4] + "_bak" + bak_filename[-4:]
                else:
                    raise
                print "%s        backing up original %s to %s" % \
                    (datetime.datetime.now().strftime("%x %X"), new_filename, bak_filename)

                # DO IT
                if not args.dryrun:
                    shutil.copy2(new_filename, bak_filename)

            # copy it
            print "%s        copying %s to %s" % \
                (datetime.datetime.now().strftime("%x %X"), model_file, new_filename)
            if not args.dryrun:
                shutil.copy2(model_file, new_filename)



