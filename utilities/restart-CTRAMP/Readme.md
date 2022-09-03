These are utilities to test the restarrt capabilities of CT-RAMP.

Specifically, we'll test if restarrting CT-RAMP for trip mode choice works.

[restart_full_test.bat] - Does the following:
  1) Sets up and runs a single iteration of model
  2) Modifies skims for test via [restart_test_modify_skims.job]
  3) Pause and request the user setup the restart parameters
  4) Keeping the Household Server, Matrix Server, and Node0 running, runs CTRAMP in restart mode.

## Notes

### Test 1: `stl`

With `RunModel.RestartWithHhServer=stl` and all `RunModel.* == false` except for `RunModel.StopLocation`, the event-node0.log was full of
exceptions like the following:

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

With `RunModel.RestartWithHhServer=stf` and all `RunModel.* == false` except for `RunModel.StopFrequency`, `RunModel.StopLocation`

Results are the same as Test 1.

### Internal References

* [Investigate running TM mode choice only (restart capability) - Asana](https://app.asana.com/0/1201809392759895/1202385716054868/f)
