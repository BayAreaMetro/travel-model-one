# travel-model-one
The Metropolitan Transportation Commission (MTC) maintains a simulation model of typical weekday travel to assist in regional planning activities.  MTC makes the software and scripts necessary to implement the model as well as detailed model results available to the public.  Users of the model and/or the model's results are entirely responsible for the outcomes, interpretations, and conclusions they reach from the information.  Users of the MTC model or model results shall in no way imply MTC's support or review of their findings or analyses.

## Model Versions
The following model versions are available in the repository:

1. Version 0.3 -- Maintained in branch [`v03`](https://github.com/BayAreaMetro/travel-model-one/tree/v03).
2. Version 0.4 -- Maintained in branch [`v04`](https://github.com/BayAreaMetro/travel-model-one/tree/v04).
3. Version 0.5 -- Maintained in branch [`v05`](https://github.com/BayAreaMetro/travel-model-one/tree/v05).
3. Version 0.6 -- Maintained in branch [`v06`](https://github.com/BayAreaMetro/travel-model-one/tree/v06).
4. Version 1.5 -- Maintained in branch [`TM1.5`](https://github.com/BayAreaMetro/travel-model-one/tree/TM1.5).
5. Version 1.6 -- Maintained in branch [`master`](https://github.com/BayAreaMetro/travel-model-one/tree/master).

Travel Model Two is also under development in a different repository: https://github.com/BayAreaMetro/travel-model-two

For additional details about the different versions, please see [here](https://github.com/BayAreaMetro/modeling-website/wiki/Development)
Any other branches are exploratory and not used in our planning work.

Please find a detailed User's Guide [here](https://github.com/BayAreaMetro/modeling-website/wiki/UsersGuide). 

Other documentation is available on the [Travel Model wiki](https://github.com/BayAreaMetro/modeling-website/wiki/TravelModel), including the [Travel Model User's Guide](https://github.com/BayAreaMetro/modeling-website/wiki/UsersGuide) and the page on [Setup and Configuration](https://github.com/BayAreaMetro/modeling-website/wiki/SetupConfiguration).



## Nick's Quickstart and migration notes

### Key Principles:
- Python First
- One Stop Shop
- Configuration Driven Overlays
- Modular and Reusable
- Trunk Driven Development (TDD)



The model is developed in a single branch, with regular commits and merges to ensure stability and avoid long-lived feature branches. Projects *should* be deployable via the scenario configuration, and not require code changes. This allows for more frequent releases and easier collaboration among developers.


- The model is now python driven --- This applies to both future ActivitySim, but also has python-runner scripts for legacy Java-based CTRAMP.


### Hints
- Configs are inherited, meaning [config_1, config_2, config_3] will apply config_3, then config_2, then config_1 in that order, allowing for easy overlays and modifications. But note that:
    - YAMLS merge, CSVs replace! Meaning a CSV overlay you need to copy-paste the entire file and make your modifications there but YAML overlays you can just specify the differences. This is a key point to understand when making modifications.



### Quickstart:
1. Clone the repository and navigate to the desired branch