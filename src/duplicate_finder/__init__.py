"""
duplicate-finder - Find and clean duplicate files.
"""

from .cleaner import clean_duplicates, removal_plan
from .scanner import scan_by_hash, scan_by_size

__version__ = "0.1.2"
__all__ = ["scan_by_size", "scan_by_hash", "clean_duplicates", "removal_plan"]
