# this script checks for error messages in setupmodel.log
# it looks for six most common errors during the model setup process:
# (1) 'the system cannot find the file specified';
# (2) 'the system cannot find the path specified';
# (3) 'The network name cannot be found';
# (4) 'The specified path is invalid';
# (5) 'The filename, directory name, or volume label syntax is incorrect'; and
# (6) [SomeProcess] is not recognized as an internal or external command'

import os, sys

ErrorInSetupModel=0

f = open('setupmodel.log')

log_contents = f.read()
print("Read {:,} chars from setupmodel.log".format(len(log_contents)))
f.close()

log_lines = log_contents.splitlines()

for line_num in range(len(log_lines)):
    if (('The system cannot find' in log_lines[line_num]) or \
        ('The network name cannot be found' in log_lines[line_num]) or \
        ('The specified path is invalid' in log_lines[line_num]) or \
        ('The filename, directory name, or volume label syntax is incorrect' in log_lines[line_num]) or \
        ('not recognized as an internal or external command' in log_lines[line_num])):

        print(f"Setupmodel.log contains errors on line {line_num+1}:\n{log_lines[line_num-1]}\n{log_lines[line_num]}")

        # return an error if setupmodel.log contains any of the above errors
        sys.exit(999)

print ("Setupmodel.log does not contain any obvious errors.")


