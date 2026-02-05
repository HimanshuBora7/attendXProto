"""
Attendance Scraper Package

This package provides functionality to scrape attendance data from the IMS portal.

Modules:
- scraper: Standalone scraper with full login flow
- scraper_with_driver: Session-based scraper for API usage
- utils: Helper functions for web scraping

Usage:
    # Standalone usage
    from scraper.scraper import scrape_attendance
    
    # API usage (with existing driver session)
    from scraper.scraper_with_driver import scrape_attendance_with_driver
"""

__version__ = "2.0.0"
__author__ = "himanshu"

# Import main functions for easy access
from .scraper_with_driver import scrape_attendance_with_driver

__all__ = ['scrape_attendance_with_driver']