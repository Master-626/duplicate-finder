# Duplicate Finder

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

Find duplicate-file candidates by size and hash. Preview a cleanup, then back up
copies or explicitly run permanent deletion.

> Start with `--dry-run` and a separate backup directory. Running `clean` without
> `--backup-dir` or `--dry-run` permanently deletes duplicate copies.

## 🌟 Features

- 🔍 **Size Scan** - Quick scan by file size to find potential duplicates
- #️⃣ **Hash Scan** - Compare MD5 hashes within same-size groups
- 🧹 **Cleanup** - Remove or backup duplicate files
- 📊 **Reports** - See how much space you can save
- 🎨 **Rich Output** - Beautiful colored terminal output

## 📦 Installation

```bash
git clone https://github.com/Master-626/duplicate-finder.git
cd duplicate-finder
pip install .
```

## 🚀 Usage

### Scan for Duplicates
```bash
# Hash-based scan (recommended, accurate)
duplicate-finder scan -d ~/Downloads

# Size-based scan (faster, less accurate)
duplicate-finder scan -d ~/Documents --method size
```

### Clean Duplicates
```bash
# Dry run first (see what would be deleted)
duplicate-finder clean -d ~/Downloads --dry-run

# Back up instead of deleting (recommended; keep oldest file)
duplicate-finder clean -d ~/Downloads --backup-dir ~/backup

# Permanently delete copies after reviewing the dry run
duplicate-finder clean -d ~/Downloads
```

### Backup behavior

- The backup directory must be outside the directory being scanned, so later
  scans do not treat backups as new duplicates.
- Existing names are never overwritten. Collisions get a numbered name, such as
  `report.1.txt`, `report.2.txt`, and so on.
- Backups require a directory on the **same filesystem** with hard-link support
  (for example NTFS, APFS, or ext4). An exclusive hard link preserves the whole
  file, including filesystem-specific metadata, before the source name is
  removed. Cross-filesystem or unsupported operations stop without removing the
  current source. Earlier files may already have been processed on an error.
- If removing a source fails after its backup link is created, both names remain
  and refer to the same file. Changing one affects the other. Existing hard links
  elsewhere also continue to share the same file; this is not an independent copy.
- File symlinks are skipped during scanning and rejected by the cleanup API.
- Backups still use disk space. The CLI reports bytes backed up, not space freed.
- `--keep oldest` and `--keep newest` use modification time. `--keep first` retains
  the first path encountered in each group; filesystem traversal order can vary.

Size-only scanning finds candidates, not proof of equal contents. MD5 comparison
is suitable for ordinary accidental duplicates, not adversarial files. Keep the
input directory unchanged while a scan and cleanup are running. This utility is
not a substitute for a separate backup or a transactional storage system.

## 🐍 Python API

```python
from pathlib import Path
from duplicate_finder import scan_by_hash, clean_duplicates

# Find duplicates
duplicates = scan_by_hash(str(Path("~/Downloads").expanduser()))

# Back up copies to a separate directory after reviewing the groups.
cleaned, moved = clean_duplicates(
    duplicates,
    keep_strategy="oldest",
    backup_dir=Path("~/duplicate-backup").expanduser(),
)
print(f"Backed up {cleaned} files ({moved} bytes)")
```

The Python API accepts groups of paths that you have already verified. `first`
uses the order in each input list. The caller must keep backups outside the scan
root; the CLI enforces this check automatically.

## 🧪 Testing

```bash
pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
python -m build
```

The regression suite covers filename collisions, repeat runs, hard-link/unlink
failures, keeper selection, dry runs, and invalid paths. GitHub Actions is
configured for Python 3.8, 3.10, 3.12 and 3.14 on Linux, plus Python 3.12 on
Windows and macOS. A workflow configuration is not a claim that every platform
has already passed.

## 📄 License

MIT License
