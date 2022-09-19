These are utilities to test the restarrt capabilities of CT-RAMP.

Specifically, we'll test if restarrting CT-RAMP for trip mode choice works.

[restart_full_test.bat](restart_full_test.bat) - Does the following:
  1) Sets up and runs a single iteration of model
  2) Modifies skims for test via [restart_test_modify_skims.job](restart_test_modify_skims.job)
  3) Pause and request the user setup the restart parameters
  4) Keeping the Household Server, Matrix Server, and Node0 running, runs CTRAMP in restart mode.

## Notes

### Test 1: `stl`

* Left all four windows running from the baseline (Matrix Manager, Household Manager, JPPF Server, Node0).
* Updated properties: `RunModel.RestartWithHhServer=stl` and all `RunModel.* == false` except for `RunModel.StopLocation`,
* Result: the event-node0.log was full of exceptions like the following:

```
02-Sep-2022 12:54:49, INFO, setting up MANDATORY time-of-day choice model.
02-Sep-2022 12:54:49, INFO, setting up JOINT_NON_MANDATORY tour frequency model on [MODEL2-D: node processing-thread-24]
02-Sep-2022 12:54:50, INFO, setting up JOINT_NON_MANDATORY tour mode choice model.
02-Sep-2022 12:55:04, INFO, creating JOINT_NON_MANDATORY tour dest choice model instance
02-Sep-2022 12:55:04, INFO, setting up JOINT_NON_MANDATORY time-of-day choice model.
02-Sep-2022 12:55:04, INFO, setting up INDIVIDUAL_NON_MANDATORY tour frequency choice model.
02-Sep-2022 12:55:06, INFO, setting up INDIVIDUAL_NON_MANDATORY tour mode choice model.
02-Sep-2022 12:55:21, INFO, creating INDIVIDUAL_NON_MANDATORY tour dest choice model instance
02-Sep-2022 12:55:22, INFO, setting up INDIVIDUAL_NON_MANDATORY time-of-day choice model.
02-Sep-2022 12:55:22, INFO, setting up AT_WORK tour frequency choice model.
02-Sep-2022 12:55:22, INFO, setting up AT_WORK tour mode choice model.
02-Sep-2022 12:55:24, INFO, creating AT_WORK subtour dest choice mode instance
02-Sep-2022 12:55:24, INFO, setting up AT_WORK tour time-of-day choice model.
02-Sep-2022 12:55:24, INFO, setting up stop frequency choice models.
02-Sep-2022 12:55:26, INFO, setting up stop location choice models.
02-Sep-2022 12:55:27, INFO, setting up trip depart time choice model.
02-Sep-2022 12:55:27, INFO, setting up trip mode choice models.
02-Sep-2022 12:55:55, INFO, setting up parking location choice models.
02-Sep-2022 12:55:55, INFO, created hhChoiceModels=89, task=102, thread=node processing-thread-24
02-Sep-2022 12:55:55, INFO, setting up AO choice model.
02-Sep-2022 12:55:56, INFO, setting up free parking choice model.
02-Sep-2022 12:55:56, INFO, setting up CDAP choice model.
02-Sep-2022 12:55:56, INFO, setting up IMTF choice model.
02-Sep-2022 12:55:57, INFO, setting up tour vehicle type choice model.
02-Sep-2022 12:55:57, INFO, setting up MANDATORY tour mode choice model.
02-Sep-2022 12:56:01, FATAL, exception caught in taskIndex=102 hhModel index=89 applying hh model for i=29, hhId=781462.
02-Sep-2022 12:56:01, FATAL, Exception caught:
java.lang.IndexOutOfBoundsException: Index: 1, Size: 1
	at java.util.ArrayList.rangeCheck(ArrayList.java:657)
	at java.util.ArrayList.get(ArrayList.java:433)
	at com.pb.models.ctramp.jppf.TourVehicleTypeChoiceModel.applyModelToAtWorkSubTours(TourVehicleTypeChoiceModel.java:214)
	at com.pb.models.ctramp.jppf.HouseholdChoiceModels.runModelsWithTiming(HouseholdChoiceModels.java:564)
	at com.pb.models.ctramp.jppf.HouseholdChoiceModelsTaskJppf.run(HouseholdChoiceModelsTaskJppf.java:102)
	at org.jppf.server.node.NodeTaskWrapper.run(NodeTaskWrapper.java:96)
	at java.util.concurrent.Executors$RunnableAdapter.call(Executors.java:511)
	at java.util.concurrent.FutureTask.run(FutureTask.java:266)
	at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1149)
	at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:624)
	at java.lang.Thread.run(Thread.java:748)
```
However, the process didn't exit.

Also, MatrixManager did not appear to reread any skims

### Test 2: `stf`

* Left all four windows running from the baseline (Matrix Manager, Household Manager, JPPF Server, Node0).
* Updated properties: `RunModel.RestartWithHhServer=stf` and all `RunModel.* == false` except for `RunModel.StopFrequency`, `RunModel.StopLocation`
* Results are the same as Test 1.

### Test 3: `stl`

* Killed and restarted Node0 (manually via GUI); left other three windows running from the baseline (Matrix Manager, Household Manager, JPPF Server).
* Updated properties: `RunModel.RestartWithHhServer=stl` and all `RunModel.* == false` except for `RunModel.StopLocation`
* Results:
  * MatrixManager is rereading skims after restart
  * event-node0.log indicates error:
```
08-Sep-2022 09:57:23, INFO, starting node
08-Sep-2022 09:57:24, INFO, Node running 24 processing threads
08-Sep-2022 09:57:30, WARN, an instance of MBean [org.jppf:name=admin,type=node] already exists, registration was skipped
08-Sep-2022 09:57:30, WARN, an instance of MBean [org.jppf:name=task.monitor,type=node] already exists, registration was skipped
08-Sep-2022 09:59:28, INFO, node processing-thread-4: HouseholdChoiceModelManager needs MatrixDataManager, MatrixDataServer connection test: testRemote() method in com.pb.models.ctramp.MatrixDataServer called.
08-Sep-2022 09:59:28, INFO, setting up stop location choice models.
08-Sep-2022 09:59:33, INFO, setting up trip depart time choice model.
08-Sep-2022 09:59:33, INFO, setting up trip mode choice models.
08-Sep-2022 09:59:39, INFO, Read landuse/tazData.csv : 985 ms
08-Sep-2022 10:05:31, INFO, setting up parking location choice models.
08-Sep-2022 10:05:31, INFO, created hhChoiceModels=1, task=1, thread=node processing-thread-4
08-Sep-2022 10:05:31, FATAL, exception caught in taskIndex=1 hhModel index=1 applying hh model for i=0, hhId=29.
08-Sep-2022 10:05:31, FATAL, Exception caught:
java.lang.RuntimeException: Cannot restart model from stl.  Must be one of: none, ao, imtf, jtf, inmtf, awf, stf.
	at com.pb.models.ctramp.jppf.HouseholdChoiceModels.checkRestartModel(HouseholdChoiceModels.java:648)
	at com.pb.models.ctramp.jppf.HouseholdChoiceModels.runModelsWithTiming(HouseholdChoiceModels.java:472)
	at com.pb.models.ctramp.jppf.HouseholdChoiceModelsTaskJppf.run(HouseholdChoiceModelsTaskJppf.java:102)
	at org.jppf.server.node.NodeTaskWrapper.run(NodeTaskWrapper.java:96)
	at java.util.concurrent.Executors$RunnableAdapter.call(Executors.java:511)
	at java.util.concurrent.FutureTask.run(FutureTask.java:266)
	at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1149)
	at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:624)
	at java.lang.Thread.run(Thread.java:748)
08-Sep-2022 10:05:31, FATAL, Throwing new RuntimeException() to terminate.
```
### Test 4: `stf`

* Didn't run from the top; used Test 3
* Killed and restarted Node0 (manually via GUI); left other three windows running from the baseline (Matrix Manager, Household Manager, JPPF Server).
* Updated properties: `RunModel.RestartWithHhServer=stf` and all `RunModel.* == false` except for `RunModel.StopFrequency`, `RunModel.StopLocation`
* Results:
  * MatrixManager is rereading skims after restart
  * event-node0.log: Appears to work!!

### Test 5: `imtf`

* Started from the top in `\\model2-d\Model2D-Sharee\Projects\2015_TM152_NGF_04_restart_test5`
* Killed and restarted Node0 (manually via GUI); left other three windows running from the baseline (Matrix Manager, Household Manager, JPPF Server).
* Updated properties: `RunModel.RestartWithHhServer=imtf` and 

```
RunModel.UsualWorkAndSchoolLocationChoice                   = false
UsualWorkAndSchoolLocationChoice.RunFlag.Work       	    = false
UsualWorkAndSchoolLocationChoice.RunFlag.University 	    = false
UsualWorkAndSchoolLocationChoice.RunFlag.School             = false
RunModel.AutoOwnership                                      = false
RunModel.FreeParking                                        = false
RunModel.CoordinatedDailyActivityPattern                    = false
RunModel.IndividualMandatoryTourFrequency                   = true
RunModel.MandatoryTourDepartureTimeAndDuration              = true
RunModel.MandatoryTourModeChoice                            = true
RunModel.JointTourFrequency                                 = true
RunModel.JointTourLocationChoice                            = true
RunModel.JointTourDepartureTimeAndDuration                  = true
RunModel.JointTourModeChoice                                = true
RunModel.IndividualNonMandatoryTourFrequency                = true
RunModel.IndividualNonMandatoryTourLocationChoice           = true
RunModel.IndividualNonMandatoryTourDepartureTimeAndDuration = true
RunModel.IndividualNonMandatoryTourModeChoice               = true
RunModel.AtWorkSubTourFrequency                             = true
RunModel.AtWorkSubTourLocationChoice                        = true
RunModel.AtWorkSubTourDepartureTimeAndDuration              = true
RunModel.AtWorkSubTourModeChoice                            = true
RunModel.StopFrequency                                      = true
RunModel.StopLocation                                       = true
```

* Results:
  * MatrixManager is rereading skims after restart
  * event-node0.log: Appears to work

### Internal References

* [Investigate running TM mode choice only (restart capability) - Asana](https://app.asana.com/0/1201809392759895/1202385716054868/f)
