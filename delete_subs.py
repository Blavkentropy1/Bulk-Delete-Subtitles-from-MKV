import os
import subprocess
import json
import argparse
import shutil
from datetime import datetime
from tqdm import tqdm
import sys
import re


###############################################################################################################################################################################################

# Configuration
DRY_RUN = False
INPUT_DIRECTORIES = os.getenv("MKV_INPUT_DIRS", "/home/Movies/,/home//Movies2/,/home//Movies3/").split(",")
LOG_DIRECTORY = os.getenv("MKV_LOG_DIR", "/home/ryan//Program/scripts/Delete_subs/")
LOG_FILE = os.path.join(LOG_DIRECTORY, "non_english_subs.log")
CHECKED_FILES_LOG = os.path.join(LOG_DIRECTORY, "checked_files.log")
MISSING_FILES_LOG = os.path.join(LOG_DIRECTORY, "missing_files.log")
DRY_RUN_FLAGGED_LOG = os.path.join(LOG_DIRECTORY, "DRYRUN-Flagged.log")

ALLOWED_SUB_LANGUAGES = ["eng", "en", "und"]
ALLOWED_SUB_LANGUAGES_STR = ",".join(ALLOWED_SUB_LANGUAGES)


###############################################################################################################################################################################################

os.makedirs(LOG_DIRECTORY, exist_ok=True)
parser = argparse.ArgumentParser(description="Remove non-English subtitles from MKV files.")
parser.add_argument("--force-recheck", action="store_true", help="Re-check all files even if logged before.")
args = parser.parse_args()
FORCE_RECHECK = args.force_recheck

checked_files = {}
if os.path.exists(CHECKED_FILES_LOG):
    with open(CHECKED_FILES_LOG, "r") as f:
        for line in f:
            try:
                file_path, mod_time = line.rsplit(" ", 1)
                checked_files[file_path] = float(mod_time)
            except ValueError:
                continue

dry_run_flagged = set(open(DRY_RUN_FLAGGED_LOG).read().splitlines()) if os.path.exists(DRY_RUN_FLAGGED_LOG) else set()

def log(message, file=LOG_FILE):
    """Log messages while keeping progress bar at bottom."""
    tqdm.write(f"{datetime.now()}: {message}")
    if not DRY_RUN:
        with open(file, "a") as log_file:
            log_file.write(f"{datetime.now()}: {message}\n")

def log_checked_file(file_path):
    mod_time = os.path.getmtime(file_path)
    checked_files[file_path] = mod_time
    with open(CHECKED_FILES_LOG, "a") as f:
        f.write(f"{file_path} {mod_time}\n")

def log_missing_file(file_path):
    if file_path in checked_files:
        log(f"File missing: {file_path}", MISSING_FILES_LOG)
        checked_files.pop(file_path, None)
        with open(CHECKED_FILES_LOG, "w") as f:
            for path, mod_time in checked_files.items():
                f.write(f"{path} {mod_time}\n")

def get_tracks_with_mkvmerge(file_path):
    try:
        result = subprocess.run(
            ["mkvmerge", "--identify", "--identification-format", "json", file_path],
            capture_output=True, text=True, check=True,
            env={**os.environ, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
        )
        return json.loads(result.stdout).get("tracks", [])
    except subprocess.CalledProcessError as e:
        log(f"Error getting track info for {file_path}: {e.stderr}")
        return []
    except Exception as e:
        log(f"Unexpected error getting track info for {file_path}: {e}")
        return []

def remove_non_english_subtitles(file_path, progress_bar, file_progress_bar):
    if not os.path.exists(file_path):
        log_missing_file(file_path)
        progress_bar.update(1)
        return

    current_mod_time = os.path.getmtime(file_path)
    if not FORCE_RECHECK and file_path in checked_files and checked_files[file_path] == current_mod_time:
        progress_bar.update(1)
        return

    log_checked_file(file_path)
    tracks = get_tracks_with_mkvmerge(file_path)
    if not tracks:
        progress_bar.update(1)
        return

    non_allowed_tracks = [
        track for track in tracks if track["type"] == "subtitles" and
        track.get("properties", {}).get("language", "unknown").lower() not in ALLOWED_SUB_LANGUAGES
    ]

    if not non_allowed_tracks:
        progress_bar.update(1)
        return

    log(f"Processing {file_path} (Non-English subtitles found)")

    # List the non-allowed subtitle languages
    non_allowed_langs = [track.get("properties", {}).get("language", "unknown") for track in non_allowed_tracks]

    if DRY_RUN:
        log_msg = f"Dry-run: {file_path} flagged for subtitle removal. Found non-allowed subtitles: {', '.join(non_allowed_langs)}"
        log(log_msg, DRY_RUN_FLAGGED_LOG)
        progress_bar.update(1)
        return

    temp_file = file_path + ".temp.mkv"
    cmd = ["mkvmerge", "-o", temp_file, "--subtitle-tracks", ALLOWED_SUB_LANGUAGES_STR, file_path]
    log(f"Constructed command: {' '.join(cmd)}")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
        )
        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            match = re.match(r"Progress: (\d+)%", line)
            if match:
                pct = int(match.group(1))
                file_progress_bar.n = pct  # Update per-file progress bar
                file_progress_bar.last_print_n = pct
                file_progress_bar.update(0)  # Force update
            else:
                tqdm.write(line)
        print()
        process.wait()
        if process.returncode == 0:
            shutil.move(temp_file, file_path)
            os.utime(file_path, None)
            log(f"Removed non-allowed subtitles from {file_path}")
        else:
            log(f"Error processing {file_path}: Command failed")
            if os.path.exists(temp_file):
                os.remove(temp_file)
    except Exception as e:
        log(f"Unexpected error processing {file_path}: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)

    progress_bar.update(1)
    tqdm.write("-" * 80)  # Separator after processing each file

if __name__ == "__main__":
    log("Starting non-English subtitle removal process.")
    files_to_process = []
    for input_dir in INPUT_DIRECTORIES:
        input_dir = input_dir.strip()
        if input_dir:
            files_to_process.extend(
                os.path.join(root, file)
                for root, _, files in os.walk(input_dir)
                for file in files if file.endswith(".mkv")
            )

    missing_files = [file for file in checked_files.keys() if not os.path.exists(file)]
    for missing_file in missing_files:
        log_missing_file(missing_file)

    with tqdm(total=len(files_to_process), desc="Overall Progress", unit="file", dynamic_ncols=True) as progress_bar:
        for file_path in files_to_process:
            with tqdm(total=100, desc=f"Processing {os.path.basename(file_path)}", position=1, leave=False) as file_progress_bar:
                remove_non_english_subtitles(file_path, progress_bar, file_progress_bar)

    log("Processing complete.")
