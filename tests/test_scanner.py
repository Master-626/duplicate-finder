import pytest

from duplicate_finder.scanner import get_file_hash, scan_by_hash, scan_by_size


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
