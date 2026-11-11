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


def _validate_strategy(keep_strategy: str) -> None:
    if keep_strategy not in {"oldest", "newest", "first"}:
        raise ValueError("keep_strategy must be oldest, newest, or first")


def _inode(file_path: Path) -> Tuple[int, int]:
    st = file_path.stat()
    return st.st_dev, st.st_ino


def removal_plan(files: List[Path], keep_strategy: str = "oldest") -> Tuple[Path, List[Path]]:
    """Choose the kept path and the directory entries that would be removed.

    ``oldest`` and ``newest`` compare ``st_mtime_ns``. Equal timestamps keep
    the earlier path in ``files`` (the sort is stable). Names that refer to
    the kept inode, including hard links and a repeated path, are not removed.
    Alias paths that resolve to one other directory entry are removed once.
    """
    _validate_strategy(keep_strategy)
    if not files:
        raise ValueError("files must not be empty")

    if keep_strategy == "first":
        keeper = files[0]
    else:
        ordered = sorted(files, key=lambda path: path.stat().st_mtime_ns)
        keeper = ordered[0] if keep_strategy == "oldest" else ordered[-1]

    keeper_id = _inode(keeper)
    to_remove = []
    seen = set()
    for file_path in files:
        if _inode(file_path) == keeper_id:
            continue
        entry = file_path.resolve()
        if entry in seen:
            continue
        seen.add(entry)
        to_remove.append(file_path)
    return keeper, to_remove


def removed_bytes(paths: List[Path], backup: bool) -> int:
    """Content bytes for ``paths``.

    Backup counts each inode once. Deletion counts an inode only when every
    remaining link is included, which is when unlinking these names frees it.
    """
    grouped = {}
    for file_path in paths:
        st = file_path.stat()
        ident = (st.st_dev, st.st_ino)
        size, nlink, count = grouped.get(ident, (st.st_size, st.st_nlink, 0))
        grouped[ident] = (size, nlink, count + 1)

    total = 0
    for size, nlink, count in grouped.values():
        if backup or nlink <= count:
            total += size
    return total


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
        ``(entries_removed, content_bytes)``. ``content_bytes`` is space freed
        when deleting, or content backed up. Hard-linked names of the kept
        inode stay in place and do not add to either number. Moving to a
        backup on the same filesystem does not reclaim physical storage.
    """
    _validate_strategy(keep_strategy)

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

        _keeper, to_remove = removal_plan(files, keep_strategy)
        freed += removed_bytes(to_remove, backup=backup_path is not None)
        for file_path in to_remove:
            if backup_path is not None:
                _backup_file(file_path, backup_path)
            else:
                file_path.unlink()
            cleaned += 1

    return cleaned, freed
