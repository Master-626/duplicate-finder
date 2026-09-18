"""
Cleaner logic for removing duplicate files.
"""

import shutil
from pathlib import Path
from typing import Dict, List, Tuple


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
        (files_cleaned, space_freed_bytes)
    """
    cleaned = 0
    freed = 0

    for file_hash, files in duplicates.items():
        if len(files) <= 1:
            continue

        # Sort by modification time
        files_sorted = sorted(files, key=lambda f: f.stat().st_mtime)

        if keep_strategy == "oldest":
            keep = files_sorted[0]
            to_remove = files_sorted[1:]
        elif keep_strategy == "newest":
            keep = files_sorted[-1]
            to_remove = files_sorted[:-1]
        else:  # first
            keep = files_sorted[0]
            to_remove = files_sorted[1:]

        for file_path in to_remove:
            size = file_path.stat().st_size

            if backup_dir:
                backup_path = Path(backup_dir)
                backup_path.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(backup_path / file_path.name))
            else:
                file_path.unlink()

            cleaned += 1
            freed += size

    return cleaned, freed
