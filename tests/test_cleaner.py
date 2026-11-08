import errno
import os
from unittest.mock import patch

import pytest

from duplicate_finder.cleaner import clean_duplicates


def make_group(tmp_path, names=("keep/report.txt", "a/report.txt", "b/report.txt")):
    files = []
    for index, name in enumerate(names):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"duplicate data")
        os.utime(path, (100 + index, 100 + index))
        files.append(path)
    return files


def test_backup_preserves_files_with_same_basename(tmp_path):
    files = make_group(tmp_path / "input")
    backup = tmp_path / "backup"
    backup.mkdir()
    existing = backup / "report.txt"
    existing.write_bytes(b"unrelated existing backup")

    assert clean_duplicates({"digest": files}, backup_dir=backup) == (2, 28)

    assert files[0].read_bytes() == b"duplicate data"
    assert all(not path.exists() for path in files[1:])
    assert existing.read_bytes() == b"unrelated existing backup"
    saved = sorted(backup.glob("report.*.txt"))
    assert len(saved) == 2
    assert all(path.read_bytes() == b"duplicate data" for path in saved)
    assert sorted(int(path.stat().st_mtime) for path in saved) == [101, 102]


def test_first_means_input_order_not_oldest(tmp_path):
    files = make_group(tmp_path)
    requested_order = [files[2], files[0], files[1]]

    clean_duplicates({"digest": requested_order}, keep_strategy="first")

    assert files[2].exists()
    assert not files[0].exists()
    assert not files[1].exists()


def test_invalid_keep_strategy_does_not_change_files(tmp_path):
    files = make_group(tmp_path)
    with pytest.raises(ValueError, match="keep_strategy"):
        clean_duplicates({"digest": files}, keep_strategy="typo")
    assert all(path.exists() for path in files)


@pytest.mark.parametrize("strategy, survivor", [("oldest", 0), ("newest", 2), ("first", 0)])
def test_keep_strategies(strategy, survivor, tmp_path):
    files = make_group(tmp_path)
    assert clean_duplicates({"digest": files}, keep_strategy=strategy) == (2, 28)
    assert [path.exists() for path in files] == [i == survivor for i in range(3)]


@pytest.mark.parametrize("error_code", [errno.EXDEV, errno.EACCES, errno.ENOSYS])
def test_failed_backup_keeps_source_and_creates_no_backup(tmp_path, error_code):
    files = make_group(tmp_path / "input", names=("first.txt", "second.txt"))
    backup = tmp_path / "backup"

    with patch(
        "duplicate_finder.cleaner.os.link", side_effect=OSError(error_code, "simulated failure")
    ):
        with pytest.raises(OSError, match="same filesystem"):
            clean_duplicates({"digest": files}, backup_dir=backup)

    assert all(path.read_bytes() == b"duplicate data" for path in files)
    assert list(backup.iterdir()) == []


def test_backup_preserves_file_identity(tmp_path):
    files = make_group(tmp_path / "input", names=("first.txt", "second.txt"))
    backup = tmp_path / "backup"
    before = files[1].stat()
    clean_duplicates({"digest": files}, backup_dir=backup)
    after = (backup / "second.txt").stat()
    assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)
    assert after.st_mtime_ns == before.st_mtime_ns
    assert after.st_mode == before.st_mode


@pytest.mark.skipif(not hasattr(os, "setxattr"), reason="extended attributes unavailable")
def test_backup_preserves_extended_attributes(tmp_path):
    files = make_group(tmp_path / "input", names=("first.txt", "second.txt"))
    backup = tmp_path / "backup"
    try:
        os.setxattr(files[1], "user.duplicate_finder", b"metadata")
    except OSError:
        pytest.skip("filesystem does not support user extended attributes")
    clean_duplicates({"digest": files}, backup_dir=backup)
    assert os.getxattr(backup / "second.txt", "user.duplicate_finder") == b"metadata"


@pytest.mark.skipif(os.name != "nt", reason="NTFS alternate streams are Windows-only")
def test_backup_preserves_ntfs_alternate_stream(tmp_path):
    files = make_group(tmp_path / "input", names=("first.txt", "second.txt"))
    backup = tmp_path / "backup"
    with open(str(files[1]) + ":extra", "wb") as stream:
        stream.write(b"alternate stream")
    clean_duplicates({"digest": files}, backup_dir=backup)
    with open(str(backup / "second.txt") + ":extra", "rb") as stream:
        assert stream.read() == b"alternate stream"


def test_cleanup_rejects_symlink_keeper_before_changing_files(tmp_path):
    files = make_group(tmp_path / "input", names=("first.txt", "second.txt"))
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(files[0])
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available")
    with pytest.raises(OSError, match="regular files"):
        clean_duplicates({"digest": [link, *files]}, keep_strategy="first")
    assert all(path.exists() for path in files)
    assert link.is_symlink()


def test_collision_with_existing_directory_is_skipped(tmp_path):
    files = make_group(tmp_path / "input", names=("first.txt", "second.txt"))
    backup = tmp_path / "backup"
    (backup / "second.txt").mkdir(parents=True)
    clean_duplicates({"digest": files}, backup_dir=backup)
    assert (backup / "second.txt").is_dir()
    assert (backup / "second.1.txt").read_bytes() == b"duplicate data"


def test_collision_with_symlink_is_skipped(tmp_path):
    files = make_group(tmp_path / "input", names=("first.txt", "second.txt"))
    backup = tmp_path / "backup"
    backup.mkdir()
    target = tmp_path / "untouched.txt"
    target.write_bytes(b"untouched")
    try:
        (backup / "second.txt").symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available")
    clean_duplicates({"digest": files}, backup_dir=backup)
    assert (backup / "second.txt").is_symlink()
    assert target.read_bytes() == b"untouched"
    assert (backup / "second.1.txt").read_bytes() == b"duplicate data"


def test_repeated_backups_do_not_overwrite_previous_copies(tmp_path):
    backup = tmp_path / "backup"
    for run in range(2):
        files = make_group(tmp_path / str(run), names=("first.txt", "second.txt"))
        clean_duplicates({"digest": files}, backup_dir=backup)
    assert {path.name for path in backup.iterdir()} == {"second.txt", "second.1.txt"}
    assert all(path.read_bytes() == b"duplicate data" for path in backup.iterdir())


def test_failed_source_removal_keeps_complete_backup(tmp_path):
    files = make_group(tmp_path / "input", names=("first.txt", "second.txt"))
    backup = tmp_path / "backup"
    with patch("pathlib.Path.unlink", side_effect=PermissionError("cannot unlink")):
        with pytest.raises(PermissionError, match="cannot unlink"):
            clean_duplicates({"digest": files}, backup_dir=backup)
    assert all(path.exists() for path in files)
    assert (backup / "second.txt").read_bytes() == b"duplicate data"


def test_invalid_backup_path_does_not_change_sources(tmp_path):
    files = make_group(tmp_path / "input")
    backup = tmp_path / "not-a-directory"
    backup.write_text("untouched")
    with pytest.raises(FileExistsError):
        clean_duplicates({"digest": files}, backup_dir=backup)
    assert all(path.exists() for path in files)
    assert backup.read_text() == "untouched"


def test_empty_and_single_file_groups_are_not_removed(tmp_path):
    files = make_group(tmp_path)
    assert clean_duplicates({}) == (0, 0)
    assert clean_duplicates({"digest": files[:1]}) == (0, 0)
    assert all(path.exists() for path in files)
