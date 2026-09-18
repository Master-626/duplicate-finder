"""
duplicate-finder - Find and clean duplicate files.
"""

from .scanner import scan_by_size, scan_by_hash
from .cleaner import clean_duplicates

__version__ = "0.1.0"
__all__ = ["scan_by_size", "scan_by_hash", "clean_duplicates"]
