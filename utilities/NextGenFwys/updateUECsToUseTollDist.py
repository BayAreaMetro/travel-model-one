USAGE = r"""

  For Horizon Futures Round 2, the model core crashed because many of the UECs include terms for auto
  distance/time and use DISTDA/TIMEDA from roadway skims.  However, since one of the strategies implemented in this
  future includes pricing all freeways, this resulted in many O/Ds without free paths in the skims, so the DISTDA/TIMEDA
  values were set to 1000000.  This would overwhelm the utilities and cause submodels to crash.

  Same is true for NextGenFwys.

  This script modifies the relevant UECs to use TOLLDISTDA and TOLLTIMEDA instead, because those values are always
  available in these runs.  Note that the mode choice models handle no-path skims for some modes, so these UECs aren't affected.

"""

import os, shutil, sys
import xlrd
import xlwt
import xlutils.copy

if __name__ == '__main__':


    file_list = os.listdir( os.path.join("CTRAMP", "model"))
    for file_name in file_list:
        # only interested in xls
        if not file_name.endswith(".xls"): continue

        # leave mode choice - they look at all modes
        if file_name in ["ModeChoice.xls","TripModeChoice.xls","accessibility_utility.xls"]: continue

        # these don't open roadway skims
        if file_name in ["accessibility_utility_constants.xls","AtWorkSubtourFrequency.xls", \
                         "CoordinatedDailyActivityPattern.xls","DestinationChoice.xls","DestinationChoiceAlternativeSample.xls", \
                         "FreeParkingEligibility.xls", "IndividualNonMandatoryTourFrequency.xls", "JointTours.xls", \
                         "ParkingLocationChoice.xls", "StopDestinationChoice.xls", "StopDestinationChoiceAlternativeSample.xls", \
                         "StopFrequency.xls", "TravelTime.xls"]: continue

        print("Updating %s" % file_name)
        filepath = os.path.join("CTRAMP","model",file_name)
        shutil.move(filepath, "%s.original" % filepath)

        xl_workbook  = xlrd.open_workbook("{}.original".format(filepath), formatting_info=True, on_demand=True)
        new_workbook = xlutils.copy.copy(xl_workbook)

        # get the data sheet
        xl_sheet = xl_workbook.sheet_by_name("data")
        sheet_names = xl_workbook.sheet_names()
        sheet_num = sheet_names.index("data")

        for rownum in range(xl_sheet.nrows):

            replacement = ""
            if xl_sheet.cell(rownum,4).value == "TIMEDA":
                replacement = " => TOLLTIMEDA"
                new_workbook.get_sheet(sheet_num).write(rownum,4,"TOLLTIMEDA")

            elif xl_sheet.cell(rownum,4).value == "DISTDA":
                replacement = " => TOLLDISTDA"
                new_workbook.get_sheet(sheet_num).write(rownum,4,"TOLLDISTDA")

            print("{: <3} {: <12} {: <10} {: <25} {: <10} {: <10} {}".format(rownum, xl_sheet.cell(rownum,1).value,
                  xl_sheet.cell(rownum,2).value, xl_sheet.cell(rownum,3).value, xl_sheet.cell(rownum,4).value, xl_sheet.cell(rownum,5).value,
                  replacement))

        new_workbook.save(filepath)

        print("")
