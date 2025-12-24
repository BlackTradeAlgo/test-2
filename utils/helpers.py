"""
NIFTY Trading System - Utility Functions
Common helper functions used across the project.
"""

import os
from datetime import datetime


def get_today_folder():
    """
    Get today's date as folder name format.
    Returns: "YYYY-MM-DD" (e.g., "2025-12-24")
    """
    return datetime.now().strftime("%Y-%m-%d")


def get_timestamp():
    """
    Get current timestamp with milliseconds.
    Returns: "HH:MM:SS.mmm" (e.g., "12:30:45.123")
    """
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def get_timestamp_full():
    """
    Get full timestamp with date.
    Returns: "YYYY-MM-DD HH:MM:SS" (e.g., "2025-12-24 12:30:45")
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_time_display():
    """
    Get time for display (without milliseconds).
    Returns: "HH:MM:SS" (e.g., "12:30:45")
    """
    return datetime.now().strftime("%H:%M:%S")


def ensure_folder_exists(folder_path):
    """
    Create folder if it doesn't exist.
    Args:
        folder_path: Path to the folder
    """
    os.makedirs(folder_path, exist_ok=True)


def format_number(value, decimals=2):
    """
    Format number with commas and decimal places.
    Args:
        value: Number to format
        decimals: Decimal places (default 2)
    Returns: Formatted string (e.g., "1,23,456.78")
    """
    if value is None:
        return "0"
    return f"{value:,.{decimals}f}"


def format_lakh(value):
    """
    Format large number in Lakhs.
    Args:
        value: Number to format
    Returns: Formatted string (e.g., "1.25L")
    """
    if value is None or value == 0:
        return "0"
    return f"{value/100000:.2f}L"


def format_crore(value):
    """
    Format large number in Crores.
    Args:
        value: Number to format
    Returns: Formatted string (e.g., "1.25Cr")
    """
    if value is None or value == 0:
        return "0"
    return f"{value/10000000:.2f}Cr"
