import glob, os, optparse

parser = optparse.OptionParser()
(options,args) = parser.parse_args()

runlevel = args[0]

scenarios = glob.glob('scenario*')
print('running model for')
print(scenarios)
print('with run level')
print(runlevel)

os.putenv('RUNLEVEL',runlevel)
os.setenv('HHSINMEM','0')
for s in scenarios:
	print('running for '+s+'...')
	os.chdir(s)
	os.system(r'copy hwy\ ..\run\hwy')
	os.system(r'copy trn\transit_lines\ ..run\trn')
	os.system(r'copy trn\transit_fares\ ..run\trn')
	os.system(r'copy trn\transit_support\ ..run\trn')
	os.chdir(r'..\run')
	
	if os.getenv('HHSINMEM') == '1':
		os.system('runQuickModel')
		
	print('calculating metrics...')
	os.system('runMetrics')
	print('copying metrics to scenario directory...')
	os.system(r'copy metrics\ ..\'+s+r'\metrics\')
	os.chdir('..')
	
	os.setenv('HHSINMEM','1')
