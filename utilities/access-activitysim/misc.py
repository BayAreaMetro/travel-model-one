import os
import warnings

import numpy as np
import orca
import pandas as pd
import yaml


warnings.filterwarnings('ignore', category=pd.io.pytables.PerformanceWarning)
pd.options.mode.chained_assignment = None


@orca.injectable()
def set_random_seed():
    pass


@orca.injectable()
def configs_dir():
    return '.'


@orca.injectable()
def settings(configs_dir):
    with open(os.path.join(configs_dir, "configs", "settings.yaml")) as f:
        return yaml.load(f)

