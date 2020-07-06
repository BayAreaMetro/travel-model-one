# this script checks for error messages in setupmodel.log
# it looks for two most common errors during the model setup process:
# (1) the system cannot find the file specified'; and
# (2) [SomeProcess] is not recognized as an internal or external command'

import os

ErrorInSetupModel=0

with open('setupmodel.log') as f:
    if 'The system cannot find the file specified' in f.read() or 'not recognized as an internal or external command' in f.read():
        ErrorInSetupModel=1
        f.close()
        print ("Setupmodel.log contains errors.")

        # produce an assertion error if setupmodel.log cotains any of the two errors
        assert ErrorInSetupModel==0

    else:
        print ("Setupmodel.log does not contain any obvious errors.")
