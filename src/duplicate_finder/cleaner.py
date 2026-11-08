"""
Cleaner logic for removing duplicate files.
"""

import os
import stat
from pathlib import Path
from typing import Dict, List, Tuple


def _backup_file(file_path: Path, backup_dir: Path) -> None:
    """Create a no-clobber hard link, then remove the source name.

    Hard links preserve the whole file, including platform-specific metadata.
    Cross-filesystem and unsupported links fail without removing the source.
    """
    index = 0
    while True:
        name = file_path.name if index == 0 else f"{file_path.stem}.{index}{file_path.suffix}"
        destination = backup_dir / name
        try:
            os.link(file_path, destination)
        except FileExistsError:
            index += 1
            continue
        except OSError as exc:
            raise OSError(
                exc.errno,
                "Cannot create backup. Use a writable directory on the same filesystem "
                "with hard-link support. The current source was not removed. " + str(exc),
            ) from exc
        break

    # Do not remove the original until the complete backup exists. If unlink
    # fails, both names remain, and the error is reported to the caller.
    file_path.unlink()


def clean_duplicates(
    duplicates: Dict[str, List[Path]],
    keep_strategy: str = "oldest",
    backup_dir: Path = None,
) -> Tuple[int, int]:
    """
    Clean duplicate files.

    Args:
        duplicates: Dict of hash -> list of file paths
        keep_strategy: Which file to keep (oldest/newest/first)
        backup_dir: If set, move duplicates here instead of deleting

    Returns:
        (files_cleaned, bytes_removed_from_source). Moving to a backup on the
        same filesystem does not reclaim physical storage.
    """
    if keep_strategy not in {"oldest", "newest", "first"}:
        raise ValueError("keep_strategy must be oldest, newest, or first")

    # Reject links and special files before changing any group. In particular,
    # retaining only a symlink while deleting its target would lose the data.
    for files in duplicates.values():
        if len(files) > 1:
            for file_path in files:
                if not stat.S_ISREG(file_path.lstat().st_mode):
                    raise OSError(f"Cleanup requires regular files, not symlinks: {file_path}")

    backup_path = Path(backup_dir).expanduser() if backup_dir is not None else None
    if backup_path is not None:
        backup_path.mkdir(parents=True, exist_ok=True)

    cleaned = 0
    freed = 0

    for files in duplicates.values():
        if len(files) <= 1:
            continue

        if keep_strategy == "first":
            to_remove = files[1:]
        else:
            files_sorted = sorted(files, key=lambda f: f.stat().st_mtime)
            to_remove = files_sorted[1:] if keep_strategy == "oldest" else files_sorted[:-1]

        for file_path in to_remove:
            size = file_path.stat().st_size

            if backup_path is not None:
                _backup_file(file_path, backup_path)
            else:
                file_path.unlink()

            cleaned += 1
            freed += size

    return cleaned, freed
