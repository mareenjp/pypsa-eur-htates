# import subprocess
# from pathlib import Path
# import yaml
# import sys

# # List your config files
# config_files = [
#     "Configs/config_2050_htates.yaml",
#     "Configs/config_2050_nohtates.yaml",
# ]

# DRY_RUN = True  # Set to True to simulate without executing

# project_dir = Path(__file__).resolve().parent

# for config_file in config_files:
#     run_name = Path(config_file).stem
#     print(f"\n--- Checking config: {config_file} ---")

#     # Load the YAML config file with correct encoding
#     try:
#         with open(config_file, encoding="windows-1252") as f:
#             config = yaml.safe_load(f)
#     except Exception as e:
#         print(f"Error reading {config_file}: {e}")
#         continue

#     # Determine results directory from config
#     results_dir = Path(config.get("results_dir", f"results/{run_name}"))

#     # Check if results_dir exists and is non-empty
#     if results_dir.exists() and any(results_dir.iterdir()):
#         print(f"Skipping {run_name}: directory '{results_dir}' already contains files.")
#         continue

#     print(f"Ready to run: {run_name} -> output to '{results_dir}'")

#     # Build snakemake command
#     # cmd = [
#     #     "snakemake", "all",
#     #     "--configfile", config_file,
#     #     "-j", "8"
#     # ]
#     cmd = [
#         "snakemake", "all",
#         "--configfile", str(config_file),
#         "-j", "8"
#     ]

#     if DRY_RUN:
#         cmd.append("--dry-run")

#     print(f"Running Snakemake for: {run_name} (dry run: {DRY_RUN})")

#     result = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)

#     if result.returncode != 0:
#         print(f"Snakemake failed for {run_name}:\n{result.stderr}")
#     else:
#         print(f"Snakemake completed for {run_name}")

import yaml
from pathlib import Path
import shutil

# Paths
scenario_yaml = Path("config/scenarios.yaml")
base_dir = Path("resources/batch_1207")
cost_file = Path("resources/costs_2030.csv")

# Load scenario names from YAML safely
with open(scenario_yaml, encoding="windows-1252") as f:
    scenarios = yaml.safe_load(f)

# Loop through each scenario
for scenario_name in scenarios.keys():
    scenario_dir = base_dir / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)

    destination = scenario_dir / "costs_2030.csv"
    shutil.copy(cost_file, destination)

    print(f"Copied to {destination}")
