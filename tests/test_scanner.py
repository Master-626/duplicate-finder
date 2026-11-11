import os

import pytest

from duplicate_finder.scanner import (
    duplicate_waste,
    format_size,
    get_file_hash,
    scan_by_hash,
    scan_by_size,
)


def test_scan_by_size(tmp_path):
    """Test scanning files by size."""
    # Create test files
    file1 = tmp_path / "file1.txt"
    file1.write_text("hello world")

    file2 = tmp_path / "file2.txt"
    file2.write_text("hello world")

    file3 = tmp_path / "file3.txt"
    file3.write_text("different content")

    duplicates = scan_by_size(str(tmp_path))
    assert len(duplicates) == 1  # Only the two same-size files


def test_scan_by_hash(tmp_path):
    """Test scanning files by hash."""
    # Create identical files
    file1 = tmp_path / "a.txt"
    file1.write_text("identical content")

    file2 = tmp_path / "b.txt"
    file2.write_text("identical content")

    file3 = tmp_path / "c.txt"
    file3.write_text("different")

    duplicates = scan_by_hash(str(tmp_path))
    assert len(duplicates) == 1
    assert len(list(duplicates.values())[0]) == 2


def test_get_file_hash(tmp_path):
    """Test file hashing."""
    file1 = tmp_path / "test.txt"
    file1.write_text("test content")

    file2 = tmp_path / "test2.txt"
    file2.write_text("test content")

    hash1 = get_file_hash(file1)
    hash2 = get_file_hash(file2)
    assert hash1 == hash2


def test_file_symlinks_are_not_duplicate_candidates(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("only one real file")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(source)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available")
    assert scan_by_size(str(tmp_path)) == {}
    assert scan_by_hash(str(tmp_path)) == {}


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (0, "0.0 B"),
        (10, "10.0 B"),
        (1023, "1023.0 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1024**2 - 1, "1.0 MB"),
        (1024**2, "1.0 MB"),
        (1024**3 - 1, "1.0 GB"),
        (1024**3, "1.0 GB"),
        (1024**4 - 1, "1.0 TB"),
        (1024**4, "1.0 TB"),
        (1024**5, "1.0 PB"),
    ],
)
def test_format_size_carries_values_that_round_to_1024(size, expected):
    assert format_size(size) == expected
    assert not format_size(size).startswith("1024.0")


def test_hard_links_are_not_extra_copies(tmp_path):
    original = tmp_path / "original.txt"
    original.write_bytes(b"z" * 50)
    linked = tmp_path / "linked.txt"
    try:
        os.link(original, linked)
    except OSError as exc:
        pytest.skip(f"hard links are not available: {exc}")

    assert scan_by_size(str(tmp_path)) == {}
    assert scan_by_hash(str(tmp_path)) == {}

    copy = tmp_path / "copy.txt"
    copy.write_bytes(b"z" * 50)
    groups = scan_by_hash(str(tmp_path))
    assert len(groups) == 1
    files = next(iter(groups.values()))
    assert {path.name for path in files} == {"original.txt", "linked.txt", "copy.txt"}
    assert duplicate_waste(files) == (1, 50)


def test_directory_symlinks_are_not_followed(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("same")
    root = tmp_path / "root"
    root.mkdir()
    (root / "local.txt").write_text("same")
    link = root / "jump"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available")

    assert scan_by_hash(str(root)) == {}


def test_hash_scan_skips_files_removed_during_hashing(tmp_path, monkeypatch):
    keep_a = tmp_path / "a.txt"
    keep_b = tmp_path / "b.txt"
    gone = tmp_path / "gone.txt"
    payload = b"same-bytes"
    keep_a.write_bytes(payload)
    keep_b.write_bytes(payload)
    gone.write_bytes(payload)

    real_hash = get_file_hash

    def flaky(path, *args, **kwargs):
        if path.name == "gone.txt":
            path.unlink()
            raise FileNotFoundError(path)
        return real_hash(path, *args, **kwargs)

    monkeypatch.setattr("duplicate_finder.scanner.get_file_hash", flaky)
    duplicates = scan_by_hash(str(tmp_path))
    assert len(duplicates) == 1
    assert {path.name for path in next(iter(duplicates.values()))} == {"a.txt", "b.txt"}
