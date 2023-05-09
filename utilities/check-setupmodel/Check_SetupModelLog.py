# this script checks for error messages in setupmodel.log
# it looks for six most common errors during the model setup process:
# (1) 'the system cannot find the file specified';
# (2) 'the system cannot find the path specified';
# (3) 'The network name cannot be found';
# (4) 'The specified path is invalid';
# (5) 'The filename, directory name, or volume label syntax is incorrect'; and
# (6) [SomeProcess] is not recognized as an internal or external command'

import os

ErrorInSetupModel=0

f = open('setupmodel.log')

log_contents = f.read()
print("Read {} chars from setupmodel.log".format(len(log_contents)))

if ('The system cannot find' in log_contents) or \
   ('The network name cannot be found' in log_contents) or \
   ('The specified path is invalid' in log_contents) or \
   ('The filename, directory name, or volume label syntax is incorrect' in log_contents) or \
   ('not recognized as an internal or external command' in log_contents):
    ErrorInSetupModel=1
    print ("Setupmodel.log contains errors.")

    # produce an assertion error if setupmodel.log cotains any of the above errors
    assert ErrorInSetupModel==0

else:
    print ("Setupmodel.log does not contain any obvious errors.")

f.close()
