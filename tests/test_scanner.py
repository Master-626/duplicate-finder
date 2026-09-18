import pytest
from pathlib import Path
from duplicate_finder.scanner import scan_by_size, scan_by_hash, get_file_hash


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
