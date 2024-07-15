import os
from update_offmodel_calculator_workbooks_with_TM_output import ABS_DIRNAME

# Input data paths
BOX_DIR = ABS_DIRNAME+r"\data\input\IPA_TM2".replace("\\","/")
MODEL_DATA_BOX_DIR = BOX_DIR+"/ModelData"

# Models
OFF_MODEL_CALCULATOR_DIR = ABS_DIRNAME+r"\models".replace("\\","/")
# Output
OFF_MODEL_CALCULATOR_DIR_OUTPUT = ABS_DIRNAME+r"\data\output".replace("\\","/")
