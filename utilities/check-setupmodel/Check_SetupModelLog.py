# check for error messages in setupmodel.log

import os

with open('setupmodel.log') as f:
    if ('The system cannot find the file specified' in f.read() OR ('not recognized as an internal or external command' in f.read()):

 #   if 'not recognized as an internal or external command' in f.read():
        print("Found errors in setupmodel")
        outfile1 = open("SetupNotOK.txt","w")#write mode
        outfile1.write("SetupNotOK \n")
        outfile1.close()
    else:
      outfile1 = open("SetupOK.txt","w")#write mode
      outfile1.write("SetupOK \n")
      outfile1.close()

print("did this run")

f.close()
