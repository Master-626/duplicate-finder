## 中文摘要

`duplicate-finder` 在目录里按文件大小和内容哈希找出重复文件。先看清单，再把多余副本备份到扫描目录之外，或明确删除。硬链接只是同一个文件的另一个名字，不算额外副本，也不会为了“去重”被删掉。两条路径如果其实指向同一份数据（重复传入同一路径，或经过目录符号链接），清理时不会把唯一的那份删掉。

```bash
pip install -e ".[dev]"
duplicate-finder scan -d ~/Downloads
duplicate-finder clean -d ~/Downloads --dry-run
duplicate-finder clean -d ~/Downloads --backup-dir ~/backup
pytest
ruff check .
```

请先使用 `--dry-run`。不带 `--backup-dir` 或 `--dry-run` 的 `clean` 会永久删除多余副本。完整说明见下文。

# Duplicate Finder

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

Find duplicate-file candidates by size and hash. Preview every path, then back up
copies or explicitly run permanent deletion.

> Start with `--dry-run` and a separate backup directory. Running `clean` without
> `--backup-dir` or `--dry-run` permanently deletes duplicate copies.

## Features

- **Size scan** — group regular files that share a byte size
- **Hash scan** — compare MD5 within each same-size group
- **Cleanup** — keep one copy and remove or back up the others
- **Reports** — list the paths and how much space an extra copy occupies
- **Rich output** — colored summary in the terminal

Hard links to one inode are one file. They are not reported as wasted space, and
cleanup leaves every name of the kept inode in place. Directory symlinks are not
followed. File symlinks are skipped by the scanner and rejected by cleanup.

## Installation

Python 3.8 or newer.

```bash
git clone https://github.com/Master-626/duplicate-finder.git
cd duplicate-finder
pip install -e ".[dev]"
```

`pip install .` is enough to use the commands. The `[dev]` extra adds pytest,
ruff, and the build tool used below. The package installs two commands that
behave the same: `duplicate-finder` and `dupf`.

## Usage

### Scan for duplicates

```bash
# Hash-based scan (default). Lists each group and a wasted-space summary.
duplicate-finder scan -d ~/Downloads

# Size-based scan. Same size is only a candidate, not proof of equal contents.
duplicate-finder scan -d ~/Documents --method size
```

A hash scan prints a summary, then one block per group:

```text
📊 Summary:
   Duplicate files: 1
   Space wasted: 14.0 B

   Groups:
   Group 1
     /home/you/Downloads/copy.txt
     /home/you/Downloads/original.txt
```

`Duplicate files` counts extra inodes. Two names of one hard-linked file add
nothing. Sizes use one decimal place and roll to the next unit instead of
printing `1024.0` of a smaller unit (`1048575` bytes is `1.0 MB`).

### Clean duplicates

```bash
# Preview the kept path and the paths that would change
duplicate-finder clean -d ~/Downloads --dry-run

# Back up copies, keep the oldest file (recommended)
duplicate-finder clean -d ~/Downloads --backup-dir ~/backup

# Keep the newest copy, still only as a preview
duplicate-finder clean -d ~/Downloads --keep newest --dry-run

# Permanently delete copies after reviewing the dry run
duplicate-finder clean -d ~/Downloads
```

`clean` always hashes file contents. It prints the same totals a real run would
report, then the plan:

```text
   Keep: /home/you/Downloads/original.txt
   Remove: /home/you/Downloads/copy.txt
```

With `--backup-dir`, each extra path is labeled `Back up` instead of `Remove`.
`--dry-run` stops after that plan and does not create the backup directory.

### Options

| Option | Command | Meaning |
| --- | --- | --- |
| `-d`, `--directory` | `scan`, `clean` | Existing directory to walk. Required. |
| `--method size\|hash` | `scan` | `hash` (default) confirms contents. `size` only groups by length. |
| `--keep oldest\|newest\|first` | `clean` | Which inode to keep. Default: `oldest`. |
| `--backup-dir PATH` | `clean` | Hard-link extras here instead of deleting them. |
| `--dry-run` | `clean` | Print the plan and change nothing. |
| `--help`, `--version` | top-level and commands | Usage and installed version. |

`--keep oldest` and `--keep newest` use nanosecond modification time
(`st_mtime_ns`). When those timestamps are equal, the earlier path in the
scanned group is kept. `--keep first` keeps the first path in each group;
directory walk order can vary between runs and filesystems.

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
- Backups still use disk space. The CLI reports content bytes backed up, once
  per inode, not space freed.
- Several names of one duplicate inode are all backed up or removed, and the
  byte count includes that content once. Names of the kept inode stay where
  they are.

Size-only scanning finds candidates, not proof of equal contents. MD5 comparison
is suitable for ordinary accidental duplicates, not adversarial files. A file
that disappears while it is being hashed is skipped; a permission error still
stops the scan. Keep the input directory unchanged while a scan and cleanup are
running. This utility is not a substitute for a separate backup or a
transactional storage system.

## Python API

```python
from pathlib import Path
from duplicate_finder import removal_plan, scan_by_hash, clean_duplicates

duplicates = scan_by_hash(str(Path("~/Downloads").expanduser()))

for files in duplicates.values():
    keeper, removals = removal_plan(files, keep_strategy="oldest")
    print(keeper)
    for path in removals:
        print(path)

cleaned, moved = clean_duplicates(
    duplicates,
    keep_strategy="oldest",
    backup_dir=Path("~/duplicate-backup").expanduser(),
)
print(f"Backed up {cleaned} files ({moved} bytes)")
```

`removal_plan` does not change the filesystem. `clean_duplicates` returns
`(entries_removed, content_bytes)`. The Python API accepts groups of paths that
you have already verified. `first` uses the order in each input list. Passing
the same path twice, or two paths that are the same directory entry, removes
nothing. The caller must keep backups outside the scan root; the CLI enforces
this check automatically.

## Testing

```bash
pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
python -m build
```

The suite covers filename collisions, repeat runs, hard-link and symlink
aliases, nanosecond keeper selection, size formatting, vanished files,
hard-link/unlink failures, dry runs, and invalid paths. GitHub Actions runs
ruff and pytest on Python 3.8 through 3.14 on Linux, plus Python 3.12 on
Windows and macOS. A workflow configuration is not a claim that every platform
has already passed.

## License

MIT License
