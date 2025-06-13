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

if __name__ == '__main__':
    M_BP_DIR = pathlib.Path("M:\\Application\\Model One\\RTP2025\\Blueprint")
    M_IP_DIR = pathlib.Path("M:\\Application\\Model One\\RTP2025\\IncrementalProgress")
    ACROSS_DIR = pathlib.Path("M:\\Application\\Model One\\RTP2025\\Blueprint\\across_runs_NetworkPerformanceAssessment")

    SCRIPT_NUM = "1A_to_1F"
    SCRIPT = pathlib.Path(f"X:\\travel-model-one-master\\utilities\\RTP\\metrics\\NPA_metrics_Goal_{SCRIPT_NUM}.py")
    for model_run_id in run_dirs.keys():
        # temp
        if run_dirs[model_run_id]!="model3-b": continue

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
        output_file = model_full_path / "metrics" / f"NPA_metrics_Goal_{SCRIPT_NUM}.csv"
        shutil.copy2(output_file, model_full_path / "extractor" / "metrics" / f"NPA_metrics_Goal_{SCRIPT_NUM}.csv")

        M_output_file = M_dir / "OUTPUT" / "metrics" / f"NPA_metrics_Goal_{SCRIPT_NUM}.csv"
        shutil.copy2(output_file, M_output_file)
        print(f"Saved output to {M_output_file}")

        M_output_file = ACROSS_DIR / f"NPA_metrics_Goal_{SCRIPT_NUM}_{model_run_id}.csv"
        shutil.copy2(output_file, M_output_file)
        print(f"Saved output to {M_output_file}")

    print("Complete")