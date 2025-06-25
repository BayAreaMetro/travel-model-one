import argparse
import pathlib
import shutil
import subprocess

run_dirs = {
    "2015_TM161_IPA_09": "model3-c",
    "2023_TM161_IPA_35": "model3-b",
    "2035_TM161_FBP_NoProject_16": "model2-c",
    "2035_TM161_FBP_Plan_16_minusTrn_01": "model2-c",
    "2035_TM161_FBP_Plan_16_minusTrnProjects_01": "model2-b",
    "2035_TM161_FBP_Plan_16": "model3-b",
    "2050_TM161_FBP_NoProject_17": "model3-c",
    "2050_TM161_FBP_Plan_16_minusTrn_01": "model3-c",
    "2050_TM161_FBP_Plan_16_minusTrnProjects_01": "model3-b",
    "2050_TM161_FBP_Plan_16": "model3-c"
}

server_to_drive = {
    'model2-b': 'B:\\',
    'model2-c': 'P:\\',
    'model3-b': 'U:\\',
    'model3-c': 'V:\\'
}

output_files = {
    '1A_to_1F': ['NPA_Metrics_Goal_1A_to_1F.csv', 'NPA_metrics_Goal_1A_to_1F.log'],
    '2':['NPA_metrics_Goal_2.csv'],
    '3':['NPA_metrics_Goal_3A_to_3D.csv','NPA_metrics_Goal_3A_to_3D_debug.csv', 'NPA_metrics_Goal_3E_3F.csv', 'NPA_metrics_Goal_3.log']
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description = "Utility for rerunning NPA metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('script_num', type=str, choices=['1A_to_1F','2','3'])
    my_args = parser.parse_args()

    M_BP_DIR = pathlib.Path("M:\\Application\\Model One\\RTP2025\\Blueprint")
    M_IP_DIR = pathlib.Path("M:\\Application\\Model One\\RTP2025\\IncrementalProgress")
    ACROSS_DIR = pathlib.Path("M:\\Application\\Model One\\RTP2025\\Blueprint\\across_runs_NetworkPerformanceAssessment")

    # SCRIPT = pathlib.Path(f"X:\\travel-model-one-master\\utilities\\RTP\\metrics\\NPA\\NPA_metrics_Goal_{my_args.script_num}.py")
    SCRIPT = pathlib.Path(f"C:\\Users\\ywang\\Documents\\GitHub\\travel-model-one\\utilities\\RTP\\metrics\\NPA\\NPA_metrics_Goal_{my_args.script_num}.py")
    for model_run_id in run_dirs.keys():
        # temp
        # if int(model_run_id[:4]) > 2025: continue

        print(f"Processing {model_run_id}")
        M_dir = M_BP_DIR / model_run_id
        if int(model_run_id[:4]) < 2025:
            M_dir = M_IP_DIR / model_run_id
        print(f" M_dir: {M_dir}")
        
        model_full_path = pathlib.Path(server_to_drive[run_dirs[model_run_id]]) / "Projects" / model_run_id
        print(f" model_full_path: {model_full_path}")

        command = ['python', str(SCRIPT)]
        result = subprocess.run(command, cwd=model_full_path, capture_output=True, text=True)
        print(f"STDOUT: {result.stdout}")
        print(f"STDOUT: {result.stderr}")

        if result.returncode != 0:
            print("Script failed!")
            print("Return code:", result.returncode)
            print("Error output:", result.stderr)
            raise
        else:
            print("Script succeeded!")
        
        # copy output
        for output_filename in output_files[my_args.script_num]:
            output_file = model_full_path / "metrics" / output_filename
            shutil.copy2(output_file, model_full_path / "extractor" / "metrics" / output_filename)

            M_output_file = M_dir / "OUTPUT" / "metrics" / output_filename
            shutil.copy2(output_file, M_output_file)
            print(f"Saved output to {M_output_file}")

            if output_filename.endswith(".log"): continue
            M_output_file = ACROSS_DIR / output_filename.replace(".csv",f"_{model_run_id}.csv")
            shutil.copy2(output_file, M_output_file)
            print(f"Saved output to {M_output_file}")

    print("Complete")