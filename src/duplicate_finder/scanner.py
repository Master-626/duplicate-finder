"""
File scanning logic for duplicate detection.
"""

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def get_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
    """Calculate MD5 hash of a file."""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)
    return md5.hexdigest()


def scan_by_size(directory: str) -> Dict[int, List[Path]]:
    """Scan directory and group files by size."""
    dir_path = Path(directory)
    size_map = defaultdict(list)

    for file_path in dir_path.rglob("*"):
        if not file_path.is_symlink() and file_path.is_file():
            size = file_path.stat().st_size
            size_map[size].append(file_path)

    # Only return groups with duplicates
    return {size: files for size, files in size_map.items() if len(files) > 1}


def scan_by_hash(directory: str) -> Dict[str, List[Path]]:
    """Scan directory and find duplicate files by hash."""
    # First group by size for efficiency
    size_dups = scan_by_size(directory)

    hash_map = defaultdict(list)

    for size, files in size_dups.items():
        for file_path in files:
            file_hash = get_file_hash(file_path)
            hash_map[file_hash].append(file_path)

    # Only return groups with duplicates
    return {file_hash: files for file_hash, files in hash_map.items() if len(files) > 1}


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
