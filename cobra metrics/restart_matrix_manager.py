import os

os.system('wmic process where ( name="java.exe" AND (commandline like "%MatrixDataServer%" or commandline like "%Dname=p1181%") ) get processid > temp.txt')
os.system('type temp.txt > ascii.txt')

f = open('ascii.txt','r')

s = f.readline()
s = f.readline()
while s != '':
	os.system('taskkill /PID ' + s + ' /F' )
	s = f.readline()
f.close()

os.chdir(r'CTRAMP\runtime')
os.system(r'JavaOnly_RestartMatrixMgr.cmd')