"""
duplicate-finder - Find and clean duplicate files.
"""

from .cleaner import clean_duplicates
from .scanner import scan_by_hash, scan_by_size

__version__ = "0.1.1"
__all__ = ["scan_by_size", "scan_by_hash", "clean_duplicates"]
