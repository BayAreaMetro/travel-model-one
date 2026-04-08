set PATH=%PATH%;C:\Program Files (x86)\Citilabs\CubeVoyager

set timeperiod=EA
runtpp X:\travel-model-one-master\utilities\create_warmstart\CreateWarmStart.job

set timeperiod=AM
runtpp X:\travel-model-one-master\utilities\create_warmstart\CreateWarmStart.job

set timeperiod=MD
runtpp X:\travel-model-one-master\utilities\create_warmstart\CreateWarmStart.job

set timeperiod=PM
runtpp X:\travel-model-one-master\utilities\create_warmstart\CreateWarmStart.job

set timeperiod=EV
runtpp X:\travel-model-one-master\utilities\create_warmstart\CreateWarmStart.job