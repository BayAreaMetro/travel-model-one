DESCRIPTION = """

    Sets up input directories for Sensitivity Tests requested by CARB in the current working dir.

    Specifically, this sets up 4 transit frequency sensitivity tests, copying transit line files
    from a pivot directory and multiplying the transit frequencies by 0.5, 0.75, 1.25 and 1.50.

"""
import os, re, sys

PIVOT_BASE_DIR=r"M:\\Application\\Model One\\RTP2017\\Scenarios\\"
PIVOT_DIR="2015_06_002"

FREQ_RE = re.compile(r"((freq\[[1-5]\][ ]*=[ ]*)(\d+[.]*\d*))", re.IGNORECASE)

if __name__ == '__main__':

    # transit frequency
    for freq_multiplier in [0.50, 0.75, 1.25, 1.50]:

        # this is the directory
        dirname = "%s_trnfreq%03d" % (PIVOT_DIR, freq_multiplier*100)

        if os.path.exists(dirname):
            print "Directory [%s] exists -- skipping" % dirname
            continue

        trn_dir = os.path.join(dirname, "INPUT", "trn", "transit_lines")
        os.makedirs(trn_dir)
        print "Created directory [%s]" % trn_dir

        src_dir = os.path.join(PIVOT_BASE_DIR, PIVOT_DIR, "INPUT", "trn", "transit_lines")
        for filename in os.listdir(src_dir):
            # we only care about tpl files
            if not str.lower(filename).endswith(".tpl"): continue

            print "  %30s" % filename,
            # create the copy
            dest_file = open(os.path.join(trn_dir, filename), 'w')
            src_file  = open(os.path.join(src_dir, filename), 'r')
            match_count = 0

            for line in src_file:

                last_end = 0
                new_line = ""
                for match in FREQ_RE.finditer(line):
                    # print "%2d-%2d: %s" % (match.start(), match.end(), match.group(1))
                    freq     = float(match.group(3))
                    new_freq = freq*freq_multiplier

                    new_freq_str = "%.1f" % new_freq
                    if float(new_freq).is_integer():
                        new_freq_str = "%d" % new_freq

                    new_line = new_line + line[last_end:match.start()] + match.group(2) + new_freq_str
                    last_end = match.end()
                    match_count += 1

                new_line = new_line + line[last_end:]

                if (False and last_end > 0):
                    print "     line=[%s]" % line.strip()
                    print " new_line=[%s]" % new_line.strip()

                dest_file.write(new_line)
            print " %3d frequencies updated" % match_count
            dest_file.close()
            src_file.close()
