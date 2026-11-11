import os
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from duplicate_finder.cli import main


def make_input(tmp_path):
    source = tmp_path / "input"
    source.mkdir()
    (source / "first.txt").write_text("duplicate")
    (source / "second.txt").write_text("duplicate")
    return source


def test_backup_command_runs(tmp_path):
    source = make_input(tmp_path)
    backup = tmp_path / "backup"
    result = CliRunner().invoke(main, ["clean", "-d", str(source), "--backup-dir", str(backup)])
    assert result.exit_code == 0, result.output
    assert len(list(source.iterdir())) == 1
    assert len(list(backup.iterdir())) == 1
    assert "Backed up 1 files" in result.output
    assert "Space to free" not in result.output
    assert "freed" not in result.output


def test_dry_run_does_not_create_backup_or_remove_files(tmp_path):
    source = make_input(tmp_path)
    backup = tmp_path / "backup"
    result = CliRunner().invoke(
        main, ["clean", "-d", str(source), "--backup-dir", str(backup), "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "no files were changed" in result.output
    assert len(list(source.iterdir())) == 2
    assert not backup.exists()


@pytest.mark.parametrize("command", ["scan", "clean"])
def test_missing_directory_is_reported(command, tmp_path):
    result = CliRunner().invoke(main, [command, "-d", str(tmp_path / "missing")])
    assert result.exit_code == 2
    assert "existing directory" in result.output


def test_backup_cannot_equal_source(tmp_path):
    source = make_input(tmp_path)
    result = CliRunner().invoke(main, ["clean", "-d", str(source), "--backup-dir", str(source)])
    assert result.exit_code == 2
    assert "outside" in result.output
    assert len(list(source.iterdir())) == 2


def test_backup_file_is_rejected(tmp_path):
    source = make_input(tmp_path)
    backup = tmp_path / "backup"
    backup.write_text("untouched")
    result = CliRunner().invoke(main, ["clean", "-d", str(source), "--backup-dir", str(backup)])
    assert result.exit_code == 2
    assert "must be a directory" in result.output
    assert len(list(source.iterdir())) == 2
    assert backup.read_text() == "untouched"


def test_cleanup_error_has_actionable_message(tmp_path):
    source = make_input(tmp_path)
    with patch("duplicate_finder.cli.clean_duplicates", side_effect=PermissionError("denied")):
        result = CliRunner().invoke(main, ["clean", "-d", str(source)])
    assert result.exit_code == 1
    assert "Cleanup stopped" in result.output
    assert "earlier files" in result.output
    assert len(list(source.iterdir())) == 2


@pytest.mark.parametrize("command", ["scan", "clean"])
def test_scan_error_is_reported(command, tmp_path):
    with patch("duplicate_finder.cli.scan_by_hash", side_effect=PermissionError("cannot read")):
        result = CliRunner().invoke(main, [command, "-d", str(tmp_path)])
    assert result.exit_code == 1
    assert "cannot read" in result.output


def test_backup_inside_scan_directory_is_rejected(tmp_path):
    source = make_input(tmp_path)
    backup = source / "backup"
    result = CliRunner().invoke(main, ["clean", "-d", str(source), "--backup-dir", str(backup)])
    assert result.exit_code == 2, result.output
    assert "outside" in result.output
    assert len(list(source.iterdir())) == 2
    assert not backup.exists()


def test_scan_lists_each_duplicate_group(tmp_path):
    source = tmp_path / "input"
    source.mkdir()
    (source / "a1.txt").write_text("alpha")
    (source / "a2.txt").write_text("alpha")
    (source / "b1.txt").write_text("beta!")
    (source / "b2.txt").write_text("beta!")

    result = CliRunner().invoke(main, ["scan", "-d", str(source)])
    assert result.exit_code == 0, result.output
    assert "Duplicate files: 2" in result.output
    assert "Group 1" in result.output
    assert "Group 2" in result.output
    for name in ("a1.txt", "a2.txt", "b1.txt", "b2.txt"):
        assert name in result.output


def test_dry_run_shows_the_kept_and_removed_paths(tmp_path):
    source = tmp_path / "input"
    source.mkdir()
    older = source / "older.txt"
    newer = source / "newer.txt"
    older.write_text("duplicate")
    newer.write_text("duplicate")
    os.utime(older, (100, 100))
    os.utime(newer, (200, 200))

    result = CliRunner().invoke(main, ["clean", "-d", str(source), "--dry-run", "--keep", "oldest"])
    assert result.exit_code == 0, result.output
    assert "Files to clean: 1" in result.output
    keep_line = next(line for line in result.output.splitlines() if "Keep:" in line)
    remove_line = next(line for line in result.output.splitlines() if "Remove:" in line)
    assert "older.txt" in keep_line
    assert "newer.txt" in remove_line
    assert older.exists() and newer.exists()

    backup = tmp_path / "backup"
    backed_up = CliRunner().invoke(
        main,
        ["clean", "-d", str(source), "--backup-dir", str(backup), "--dry-run"],
    )
    assert backed_up.exit_code == 0, backed_up.output
    assert "Back up:" in backed_up.output
    assert "Remove:" not in backed_up.output
    assert not backup.exists()


def test_clean_reports_one_copy_when_other_names_are_hard_links(tmp_path):
    source = tmp_path / "input"
    source.mkdir()
    kept = source / "kept.txt"
    alias = source / "alias.txt"
    copy = source / "copy.txt"
    payload = b"z" * 50
    kept.write_bytes(payload)
    copy.write_bytes(payload)
    try:
        os.link(kept, alias)
    except OSError as exc:
        pytest.skip(f"hard links are not available: {exc}")
    os.utime(kept, (100, 100))
    os.utime(copy, (200, 200))

    preview = CliRunner().invoke(main, ["scan", "-d", str(source)])
    assert preview.exit_code == 0, preview.output
    assert "Duplicate files: 1" in preview.output
    assert "50.0 B" in preview.output
    for name in ("kept.txt", "alias.txt", "copy.txt"):
        assert name in preview.output

    result = CliRunner().invoke(main, ["clean", "-d", str(source), "--keep", "oldest"])
    assert result.exit_code == 0, result.output
    assert "Files to clean: 1" in result.output
    assert "Cleaned 1 files, freed 50.0 B" in result.output
    assert kept.read_bytes() == payload
    assert alias.read_bytes() == payload
    assert not copy.exists()
