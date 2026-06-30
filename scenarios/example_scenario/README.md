# Example Scenario: WFH Policy Boost

Demonstrates how scenario overlays work in TM1.

## What this scenario does

Applies an EN7-style telecommuting encouragement policy: a +0.5 utility boost
to Work From Home for workers whose workplace is in San Francisco
(superdistricts 1–6). This increases WFH rates for SF-destined workers by
roughly 10–15 percentage points depending on other person/household attributes.

## How it works

The only model file overridden is `activitysim/work_from_home.csv`. Because
ActivitySim's config directory chain uses **first-directory-wins** resolution,
placing this file in the scenario's `activitysim/` folder means it takes
priority over the base model version in `base-models/activity/configs/`.

Everything else — coefficients, mode choice specs, scheduling, etc. — comes
from the base model unchanged.

## Directory structure

```
scenarios/example_scenario/
├── scenario_config.yaml              # pipeline config + machine paths
├── activitysim/
│   ├── settings.yaml                 # small sample, no shadow pricing
│   └── work_from_home.csv           # WFH spec with SF boosts activated
└── populationsim/                    # empty — uses base PopulationSim
```

## Running

```bash
tm1 run --scenario scenarios/example_scenario
```

Or for a quick test with 100 households:

```bash
tm1 run --scenario scenarios/example_scenario --sample-rate 0.01
```
