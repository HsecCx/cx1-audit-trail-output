"""
Scan Results Fetcher Module

This module handles fetching and processing scan results from the Checkmarx One API.
Includes support for server-side date filtering and pagination.
"""

import logging
from datetime import datetime
from typing import Optional, Dict
from urllib.parse import urlencode

import requests
from dateutil.parser import isoparse

from utils.generate_oauth_token import load_config

logger = logging.getLogger(__name__)

CONFIGS = load_config()
BASE_API_URL = CONFIGS["api_url"]


def get_response(url: str, headers: dict) -> dict:
    """
    Helper function to make a GET request to the specified URL with the provided headers.

    Args:
        url (str): The URL to send the GET request to.
        headers (dict): The headers to include in the request.

    Returns:
        dict: The JSON response from the API.
    """
    response = requests.get(url, headers=headers)
    if response.ok:
        return response.json()
    else:
        logger.error(f"GET {url} failed with {response.status_code}: {response.text}")
        raise RuntimeError(f"GET {url} failed with status code {response.status_code}")


def parse_flexible_date(date_str: str) -> datetime:
    """
    Parses a date string in either MM/DD/YYYY or MM/DD/YY format into a datetime object.

    Args:
        date_str (str): The date string to parse.

    Returns:
        datetime: A datetime object representing the parsed date.
    """
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Date '{date_str}' is not in MM/DD/YY or MM/DD/YYYY format.")


def convert_date_to_rfc3339(date_str: str, is_end_date: bool = False) -> str:
    """
    Converts a date string from MM/DD/YYYY format to RFC3339 format for API calls.
    
    Args:
        date_str (str): Date in MM/DD/YYYY or MM/DD/YY format
        is_end_date (bool): If True, sets time to end of day to include all events on that date
        
    Returns:
        str: Date in RFC3339 format (e.g. 2021-06-02T00:00:00.000Z)
    """
    if not date_str:
        return None
    
    dt = parse_flexible_date(date_str)
    
    # For end dates, set to end of day to include all events on that date
    if is_end_date:
        return dt.strftime("%Y-%m-%dT23:59:59.999Z")
    
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def add_formatted_date_for_scans(scans: list, fmt: str = "%m/%d/%Y %H:%M") -> list:
    """
    Adds a formatted, Excel-friendly date string to each scan in the list.

    Args:
        scans (list): A list of dictionaries, each containing scan data.
        fmt (str, optional): A datetime format string to apply.

    Returns:
        list: The modified list of dictionaries with formatted dates.
    """
    for scan in scans:
        try:
            # Scans might have different date fields than audit events
            date_field = None
            for field in ['createdAt', 'updatedAt', 'scanDate', 'dateTime']:
                if field in scan:
                    date_field = field
                    break
            
            if date_field:
                parsed_dt = isoparse(scan[date_field])
                scan["FormattedEventDate"] = parsed_dt.strftime(fmt)
        except Exception as e:
            logger.error(f"Error adding formatted datetime to scan: {scan}. Error: {e}")
    return scans


def get_default_date_range() -> tuple:
    """Get default date range (last 30 days including today)."""
    from datetime import datetime, timedelta
    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)
    return (
        thirty_days_ago.strftime("%m/%d/%Y"),
        today.strftime("%m/%d/%Y")
    )

def get_scan_results(headers: dict, from_date: str = None, to_date: str = None, 
                    limit: int = 1000, offset: int = 0) -> dict:
    """
    Retrieves scan results from the Scans API with proper parameter handling.
    
    Args:
        headers (dict): HTTP headers including Authorization token.
        from_date (str, optional): Start date in MM/DD/YY or MM/DD/YYYY format.
        to_date (str, optional): End date in MM/DD/YY or MM/DD/YYYY format.
        limit (int): Maximum number of results to return (default: 1000).
        offset (int): Number of results to skip (default: 0).
        
    Returns:
        dict: Dictionary containing scan results and metadata.
    """
    
    # Build base URL
    base_url = f"{BASE_API_URL}/scans"
    params = {}
    
    # Add pagination parameters
    params["limit"] = limit
    params["offset"] = offset
    
    # Convert dates to RFC3339 format and add as query parameters
    if from_date:
        rfc3339_from = convert_date_to_rfc3339(from_date, is_end_date=False)
        params["from-date"] = rfc3339_from
        logger.info(f"Using server-side from-date filter: {rfc3339_from}")
    
    if to_date:
        rfc3339_to = convert_date_to_rfc3339(to_date, is_end_date=True)
        params["to-date"] = rfc3339_to
        logger.info(f"Using server-side to-date filter: {rfc3339_to}")
    
    # Build URL with properly encoded query parameters
    url = base_url + "?" + urlencode(params)
    
    logger.debug(f"\n{'=' * 200}\nMaking request to scan results from {url} for tenant {CONFIGS['tenant_name']}\n{'=' * 200}\n")
    logger.info(f"Making request to scan results api for tenant {CONFIGS['tenant_name']}")
    try:
        scan_request_response = get_response(url, headers)
        scans = scan_request_response.get("scans", [])
        
        # Add formatted dates for Excel compatibility
        scans = add_formatted_date_for_scans(scans)
        
        logger.info(f"Retrieved {len(scans)} scans from API")
        
        return {
            "scans": scans,
            "total_count": len(scans),
            "limit": limit,
            "offset": offset,
            "url": url
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve scan results: {e}")
        return {
            "scans": [],
            "total_count": 0,
            "limit": limit,
            "offset": offset,
            "url": url,
            "error": str(e)
        }
