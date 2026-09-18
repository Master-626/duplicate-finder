# Duplicate Finder

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

Find and clean duplicate files by size and hash. Free up disk space easily.

## 🌟 Features

- 🔍 **Size Scan** - Quick scan by file size to find potential duplicates
- #️⃣ **Hash Scan** - Accurate detection using MD5 hash comparison
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

# Actually clean (keep oldest file)
duplicate-finder clean -d ~/Downloads

# Backup instead of delete
duplicate-finder clean -d ~/Downloads --backup-dir ~/backup
```

## 🐍 Python API

```python
from duplicate_finder import scan_by_hash, clean_duplicates

# Find duplicates
duplicates = scan_by_hash("~/Downloads")

# Clean them
cleaned, freed = clean_duplicates(duplicates, keep_strategy="oldest")
print(f"Cleaned {cleaned} files, freed {freed} bytes")
```

## 🧪 Testing

```bash
pip install -e ".[dev]"
pytest
```

## 📄 License

MIT License
