
import os

# from update_offmodel_calculator_workbooks_with_TM_output import ABS_DIRNAME
# ABS_DIRNAME=r"C:\Users\63330\Documents\projects\MTC\travel-model-one\utilities\RTP\Emissions\Off Model Calculators".replace("\\","/")
ABS_DIRNAME=os.path.join(os.path.dirname(__file__),"..").replace("\\","/")
# Input data paths
BOX_DIR = ABS_DIRNAME+r"\data\input\IPA_TM2".replace("\\","/")
MODEL_DATA_BOX_DIR = BOX_DIR+"/ModelData"

# Models
OFF_MODEL_CALCULATOR_DIR = ABS_DIRNAME+r"\models".replace("\\","/")
# Output
OFF_MODEL_CALCULATOR_DIR_OUTPUT = ABS_DIRNAME+r"\data\output".replace("\\","/")

# Variables locations
VARS=ABS_DIRNAME+r"\models\Variable_locations.xlsx".replace("\\","/")