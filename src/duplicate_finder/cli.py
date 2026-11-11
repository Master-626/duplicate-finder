"""
CLI interface for duplicate-finder.
"""

from pathlib import Path

import click
from rich.console import Console

from .cleaner import clean_duplicates, removal_plan, removed_bytes
from .scanner import duplicate_waste, format_size, scan_by_hash, scan_by_size

# Keep paths on one line so a wrapped filename is not cut in half.
console = Console(soft_wrap=True)


def _scan_directory(value):
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise click.BadParameter("must be an existing directory", param_hint="--directory")
    return path


def _print_groups(duplicates):
    """List every path in each duplicate group."""
    if not duplicates:
        return
    console.print("\n   Groups:")
    for index, files in enumerate(duplicates.values(), start=1):
        console.print(f"   Group {index}")
        for file_path in sorted(files, key=str):
            console.print(f"     {file_path}", markup=False)


def _print_plan(plans, backup):
    """Show the kept path and each path that would be removed or backed up."""
    action = "Back up" if backup else "Remove"
    printed = False
    for keeper, removals in plans:
        if not removals:
            continue
        if printed:
            console.print()
        printed = True
        console.print(f"   Keep: {keeper}", markup=False)
        for file_path in removals:
            console.print(f"   {action}: {file_path}", markup=False)


@click.group()
@click.version_option()
def main():
    """Duplicate Finder - Find and clean duplicate files."""
    pass


@main.command()
@click.option("-d", "--directory", required=True, help="Directory to scan")
@click.option("--method", default="hash", type=click.Choice(["size", "hash"]), help="Scan method")
def scan(directory, method):
    """Scan directory for duplicate files."""
    directory = _scan_directory(directory)
    console.print(f"\n🔍 Scanning: {directory}")

    try:
        if method == "size":
            duplicates = scan_by_size(directory)
            console.print(f"   Found {len(duplicates)} groups with same size")
        else:
            duplicates = scan_by_hash(directory)
            console.print(f"   Found {len(duplicates)} duplicate groups")
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc

    # Show summary. Count inodes, so hard-linked names are not extra copies.
    total_dups = 0
    total_size = 0
    for files in duplicates.values():
        extra, wasted = duplicate_waste(files)
        total_dups += extra
        total_size += wasted

    console.print("\n📊 Summary:")
    console.print(f"   Duplicate files: {total_dups}")
    console.print(f"   Space wasted: {format_size(total_size)}")
    _print_groups(duplicates)


@main.command()
@click.option("-d", "--directory", required=True, help="Directory to scan")
@click.option(
    "--keep",
    default="oldest",
    type=click.Choice(["oldest", "newest", "first"]),
    help="Which file to keep",
)
@click.option("--backup-dir", help="Backup directory (instead of deleting)")
@click.option("--dry-run", is_flag=True, help="Show what would be done without actually doing it")
def clean(directory, keep, backup_dir, dry_run):
    """Clean duplicate files."""
    directory = _scan_directory(directory)
    backup_path = Path(backup_dir).expanduser().resolve() if backup_dir is not None else None
    if backup_path is not None:
        if backup_path == directory or directory in backup_path.parents:
            raise click.BadParameter(
                "must be outside the scan directory so backups are not scanned again",
                param_hint="--backup-dir",
            )
        if backup_path.exists() and not backup_path.is_dir():
            raise click.BadParameter("must be a directory", param_hint="--backup-dir")
    try:
        duplicates = scan_by_hash(directory)
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc

    plans = []
    for files in duplicates.values():
        if len(files) <= 1:
            continue
        plans.append(removal_plan(files, keep))
    removals = [path for _keeper, to_remove in plans for path in to_remove]
    total_dups = len(removals)
    total_size = removed_bytes(removals, backup=backup_path is not None)

    console.print("\n🧹 Cleanup Summary:")
    console.print(f"   Files to clean: {total_dups}")
    label = "Bytes to back up" if backup_path is not None else "Space to free"
    console.print(f"   {label}: {format_size(total_size)}")
    if removals:
        console.print()
        _print_plan(plans, backup=backup_path is not None)

    if dry_run:
        console.print("\n   [yellow]Dry run - no files were changed[/yellow]")
        return

    try:
        cleaned, freed = clean_duplicates(
            duplicates,
            keep_strategy=keep,
            backup_dir=backup_path,
        )
    except OSError as exc:
        raise click.ClickException(
            f"Cleanup stopped: {exc}. Some earlier files may already have been processed."
        ) from exc

    if backup_path is not None:
        console.print(f"\n✅ Backed up {cleaned} files ({format_size(freed)}) to {backup_path}")
        console.print("   Backups still occupy storage; no disk-space saving is claimed.")
    else:
        console.print(f"\n✅ Cleaned {cleaned} files, freed {format_size(freed)}")


if __name__ == "__main__":
    main()
