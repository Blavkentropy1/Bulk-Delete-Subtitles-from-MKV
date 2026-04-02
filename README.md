# MKV Subtitle Cleaner

A Python script that scans `.mkv` files and removes non-English subtitle tracks, keeping your media library clean and consistent.

It uses `mkvmerge` to safely rewrite files while preserving only allowed subtitle languages.

---

## What It Does

* Recursively scans one or more directories for `.mkv` files
* Detects subtitle tracks using `mkvmerge`
* Removes subtitles that are not in allowed languages (default: English)
* Tracks previously processed files to avoid unnecessary reprocessing
* Logs:

  * Processed files
  * Missing files
  * Files flagged during dry runs
* Supports a dry-run mode to preview changes without modifying files
* Displays progress using `tqdm` progress bars

---

## Pre-requisites

Make sure the following are installed:

### 1. Python

Python 3.7+ recommended

### 2. MKVToolNix

Provides `mkvmerge`, which is required.

Install via package manager:

```bash
# Ubuntu/Debian
sudo apt install mkvtoolnix

# Arch / Artix
sudo pacman -S mkvtoolnix-cli
```

### 3. Python Dependencies

Install required Python packages:

```bash
pip install tqdm
```

---

## Usage

### Basic run:

```bash
python script.py
```

### Force re-check all files:

```bash
python script.py --force-recheck
```

---

## Variables to Edit

You can configure behavior via environment variables or directly in the script.

### Input Directories

```python
INPUT_DIRECTORIES = os.getenv(
    "MKV_INPUT_DIRS",
    "/home/Movies/,/home/Movies2/,/home//Movies3/"
).split(",")
```
---

### Log Directory

```python
LOG_DIRECTORY = os.getenv(
    "MKV_LOG_DIR",
    "/home/Program/scripts/Delete_subs/"
)
```

Stores:

* `non_english_subs.log`
* `checked_files.log`
* `missing_files.log`
* `DRYRUN-Flagged.log`

---

### Allowed Subtitle Languages

```python
ALLOWED_SUB_LANGUAGES = ["eng", "en", "und"]
```

* Uses ISO language codes

Default keeps:

* `eng` → English
* `en` → English (alternative code)
* `und` → Undefined (often safe to keep)

Modify to suit your needs:

```python
ALLOWED_SUB_LANGUAGES = ["eng", "jpn"]
```

---

### Dry Run Mode

```python
DRY_RUN = False
```

* Set to `True` to simulate changes only
* No files will be modified
* Flagged files will be logged instead

---
