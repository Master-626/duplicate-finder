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
