"""
File scanning logic for duplicate detection.
"""

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

_SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]


def get_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
    """Calculate MD5 hash of a file."""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)
    return md5.hexdigest()


def _collect_file(file_path: Path, size_map, inodes) -> None:
    """Record one regular file. Missing files and links are ignored."""
    try:
        if file_path.is_symlink() or not file_path.is_file():
            return
        st = file_path.stat()
    except FileNotFoundError:
        return
    size_map[st.st_size].append(file_path)
    inodes[st.st_size].add((st.st_dev, st.st_ino))


def scan_by_size(directory: str) -> Dict[int, List[Path]]:
    """Scan directory and group files by size.

    Hard links to one inode are a single file, so a size is returned only when
    at least two inodes share it. Directory symlinks are not followed.
    """
    dir_path = Path(directory)
    size_map = defaultdict(list)
    inodes = defaultdict(set)

    for file_path in dir_path.rglob("*"):
        _collect_file(file_path, size_map, inodes)

    return {size: files for size, files in size_map.items() if len(inodes[size]) > 1}


def scan_by_hash(directory: str) -> Dict[str, List[Path]]:
    """Scan directory and find duplicate files by hash.

    Files that disappear while hashing are skipped. Hard-linked names of a
    single inode are not reported as extra copies.
    """
    # First group by size for efficiency
    size_dups = scan_by_size(directory)

    hash_map = defaultdict(list)
    inodes = defaultdict(set)

    for files in size_dups.values():
        for file_path in files:
            try:
                file_hash = get_file_hash(file_path)
                st = file_path.stat()
            except FileNotFoundError:
                continue
            hash_map[file_hash].append(file_path)
            inodes[file_hash].add((st.st_dev, st.st_ino))

    return {file_hash: files for file_hash, files in hash_map.items() if len(inodes[file_hash]) > 1}


def duplicate_waste(files: List[Path]) -> Tuple[int, int]:
    """Return ``(extra_copies, wasted_bytes)`` for one group.

    Each inode counts once. Wasted bytes are every inode except the largest,
    which is the same as ``(inodes - 1) * size`` for scanner groups.
    """
    sizes = {}
    for file_path in files:
        try:
            st = file_path.stat()
        except FileNotFoundError:
            continue
        sizes.setdefault((st.st_dev, st.st_ino), st.st_size)
    if len(sizes) <= 1:
        return 0, 0
    values = list(sizes.values())
    return len(values) - 1, sum(values) - max(values)


def format_size(size_bytes: int) -> str:
    """Format a byte count with one decimal place.

    A value that would render as 1024.0 of a unit is carried into the next
    unit, so 1048575 bytes is ``1.0 MB`` rather than ``1024.0 KB``.
    """
    size = float(size_bytes)
    unit = _SIZE_UNITS[-1]
    rendered = f"{size:.1f}"
    for unit in _SIZE_UNITS:
        rendered = f"{size:.1f}"
        if unit == _SIZE_UNITS[-1] or float(rendered) < 1024:
            break
        size /= 1024
    return f"{rendered} {unit}"
