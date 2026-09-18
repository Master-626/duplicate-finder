"""
CLI interface for duplicate-finder.
"""

import click
from rich.console import Console
from rich.table import Table

from .scanner import scan_by_size, scan_by_hash, format_size
from .cleaner import clean_duplicates

console = Console()


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
    console.print(f"\n🔍 Scanning: {directory}")

    if method == "size":
        duplicates = scan_by_size(directory)
        console.print(f"   Found {len(duplicates)} groups with same size")
    else:
        duplicates = scan_by_hash(directory)
        console.print(f"   Found {len(duplicates)} duplicate groups")

    # Show summary
    total_dups = sum(len(files) - 1 for files in duplicates.values())
    total_size = sum(
        files[0].stat().st_size * (len(files) - 1)
        for files in duplicates.values()
    )

    console.print(f"\n📊 Summary:")
    console.print(f"   Duplicate files: {total_dups}")
    console.print(f"   Space wasted: {format_size(total_size)}")


@main.command()
@click.option("-d", "--directory", required=True, help="Directory to scan")
@click.option("--keep", default="oldest", type=click.Choice(["oldest", "newest", "first"]), help="Which file to keep")
@click.option("--backup-dir", help="Backup directory (instead of deleting)")
@click.option("--dry-run", is_flag=True, help="Show what would be done without actually doing it")
def clean(directory, keep, backup_dir, dry_run):
    """Clean duplicate files."""
    duplicates = scan_by_hash(directory)

    total_dups = sum(len(files) - 1 for files in duplicates.values())
    total_size = sum(
        files[0].stat().st_size * (len(files) - 1)
        for files in duplicates.values()
    )

    console.print(f"\n🧹 Cleanup Summary:")
    console.print(f"   Files to clean: {total_dups}")
    console.print(f"   Space to free: {format_size(total_size)}")

    if dry_run:
        console.print("\n   [yellow]Dry run - no files were actually removed[/yellow]")
        return

    cleaned, freed = clean_duplicates(
        duplicates,
        keep_strategy=keep,
        backup_dir=Path(backup_dir) if backup_dir else None,
    )

    console.print(f"\n✅ Cleaned {cleaned} files, freed {format_size(freed)}")


if __name__ == "__main__":
    main()
