
import os

# Input data paths
BOX_DIR = 'C:\Users\{}\Box\Plan Bay Area 2050+\Blueprint\Off-Model\PBA50+ Off-Model'.format(os.environ.get('USERNAME'))
MODEL_DATA_BOX_DIR = os.path.join(BOX_DIR, 'model_data_all')

# Models
OFF_MODEL_CALCULATOR_DIR = os.path.join(BOX_DIR, 'DBP_v2', 'PBA50+ Off-Model Calculators')

# Outputs
OFF_MODEL_CALCULATOR_DIR_OUTPUT = OFF_MODEL_CALCULATOR_DIR