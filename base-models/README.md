# base-models

This is where the base model assets live. The base model is the starting point for all scenarios, and should be a complete, runnable model. It should include all the necessary configs, specs, lookup tables, and default assets to run the model end-to-end; **EXCEPT** data files, which are kept out of the repo and should be fetched/referenced separately. The only acceptable data files in the base model are small (e.g. <1MB), not expected to change often, and do not contain personally identifiable information (PII).

Base models then get scenario-specific overrides, such as:
- Network differences
- Land use differences
- Population (households/persons) differences
- Model configuration differences (e.g. different model components, or different model parameters)

Scenario overrides should be kept in the `scenarios/` directory, and should only include the differences from the base model.


## Base models
The current working base model in development I'm calling `tm1a` (`a` for `activitysim`, and `awesome`) which is a direct descendant of the original TM1 model. 

```travel-model-one v0.3 --> prototype_mtc --> tm1a```

Activitysim maintains two MTC prototype examples for testing purposes, but serve as a useful starting point for us. Here's some history:

    The `prototype_mtc` example is based on (but has evolved away from) the
    [Bay Area Metro Travel Model One](https://github.com/BayAreaMetro/travel-model-one), 
    also known as "TM1". TM1 has its roots in a wide array of analytical approaches, 
    including discrete choice forms (multinomial and nested logit models), activity 
    duration models, time-use models, models of individual micro-simulation with 
    constraints, entropy-maximization models, etc. These tools are combined in the 
    model design to realistically represent travel behavior, adequately replicate 
    observed activity-travel patterns, and ensure model sensitivity to infrastructure
    and policies. The model is implemented in a micro-simulation framework. Microsimulation
    methods capture aggregate outcomes through the representation of the behavior of
    individual decision-makers.

    There are two model structures in the `prototype_mtc` example: a simpler model that is
    relatively close to the TM1 model, and a more complex model that is incorporates
    new model components that have been added by the ActivitySim consortium over the
    past few years.

    See https://activitysim.github.io for more information.

The tricky part is that while `prototype_mtc` is a port of an earlier version `TM1 V0.3`, it was modified in various ways during the porting process, and has also been updated with new features and capabilities since then.

So while it's very similar, its not exactly the same as the original TM1 V0.03, even from the original port. There's no easy one-to-one diff between the two, and the differences are not always well-documented. But that's okay! The important thing is that `prototype_mtc` is a working base model that we can use as a starting point for our own development.


