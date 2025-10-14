"""
Objects Package

This package contains the core functionality modules for the Checkmarx One Data Fetcher.
"""

from .audit_fetcher import get_audit_events
from .scan_fetcher import get_scan_results
from .output import OutputManager

__all__ = [
    'get_audit_events',
    'get_scan_results', 
    'OutputManager'
]

__version__ = '1.0.0'
