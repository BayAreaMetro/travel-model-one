"""Build-once input staging: pristine ``INPUT/`` files -> model-loop inputs.

Every step in this package runs after ``copy_inputs`` and before ``iterate:``,
building an artifact the loop consumes but never rewrites.  They are grouped
here because they share a fate as well as a position: each wraps Cube-era
tooling behind a step whose *artifact* outlives Cube — see the retirement
warning in each module's docstring for what to delete versus re-implement
when the engine goes.

- :mod:`~tm1.steps.build.highway_networks` — tolls.csv -> tolls.dbf (native),
  then SetTolls/SetHovXferPenalties/CreateFiveHighwayNetworks as-is.
- :mod:`~tm1.steps.build.nonmotorized_skims` — CreateNonMotorizedNetwork +
  NonMotorizedSkims as-is -> ``skims/nonmotskm.tpp``.
"""
