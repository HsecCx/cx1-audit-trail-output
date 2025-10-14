"""
Audit Events Fetcher Module

This module handles fetching and processing audit events from the Checkmarx One API.
Includes threading support for pagination and date filtering capabilities.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Optional, Dict
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

    Raises:
        ValueError: If the input does not match any of the supported formats.
    """
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Date '{date_str}' is not in MM/DD/YY or MM/DD/YYYY format.")


def add_formatted_date(items: list, fmt: str = "%m/%d/%Y %H:%M") -> list:
    """
    Adds a formatted, Excel-friendly date string to each audit event in the list.

    Args:
        items (list): A list of dictionaries, each containing an 'eventDate' key.
        fmt (str, optional): A datetime format string to apply. Defaults to "%m/%d/%Y %H:%M".

    Returns:
        list: The modified list of dictionaries, each now containing a 'FormattedEventDate' field.
    """
    for item in items:
        try:
            parsed_dt = isoparse(item["eventDate"])
            item["FormattedEventDate"] = parsed_dt.strftime(fmt)
        except Exception as e:
            logger.error(f"Error adding formatted datetime to item: {item}. Error: {e}")
    return items


def filter_by_date(events: list, from_date: str, to_date: str) -> List[dict]:
    """
    Filters a list of audit events based on a date range.

    Args:
        events (list): A list of dictionaries, each representing an audit event.
        from_date (str): Start date as a string in MM/DD/YY or MM/DD/YYYY format.
        to_date (str): End date as a string in MM/DD/YY or MM/DD/YYYY format.

    Returns:
        list: A list of audit events that fall within the specified date range.
    """
    from_dt = parse_flexible_date(from_date) if from_date else None
    to_dt = parse_flexible_date(to_date) if to_date else None
    filtered_events = []
    
    for event in events:
        try:
            event_dt = isoparse(event["eventDate"])
            if (
                (from_dt is None or event_dt.date() >= from_dt.date()) and
                (to_dt is None or event_dt.date() <= to_dt.date())
            ):
                filtered_events.append(event)
        except Exception as e:
            logger.error(f"Error filtering by date: {e}")
            continue

    return filtered_events


def fetch_events_from_link(headers: dict, link: dict) -> tuple:
    """
    Fetches audit events from a given pagination link.

    Args:
        headers (dict): HTTP headers including the Authorization token.
        link (dict): A dictionary containing the 'url' key pointing to the API endpoint.

    Returns:
        tuple: A tuple containing events_result and curl_cmd.
    """
    link_url = link["url"]
    logger.debug(f"Processing link {link_url}")
    events_result = get_response(link_url, headers)
    curl_cmd = f"curl -X GET '{link_url}' -H 'Authorization: Bearer <token>'"
    return events_result, curl_cmd


def get_default_date_range() -> tuple:
    """Get default date range (last 30 days including today)."""
    from datetime import datetime, timedelta
    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)
    return (
        thirty_days_ago.strftime("%m/%d/%Y"),
        today.strftime("%m/%d/%Y")
    )

def get_audit_events(headers: dict, from_date: Optional[str] = None, 
                    to_date: Optional[str] = None, thread_count: Optional[int] = 4) -> dict:
    """
    Retrieves and filters audit events from the Audit API.

    Args:
        headers (dict): HTTP headers including Authorization token.
        from_date (str, optional): Start date for filtering events.
        to_date (str, optional): End date for filtering events.
        thread_count (int, optional): Number of threads to use for fetching paginated events.

    Returns:
        dict: A dictionary containing events, links, and curl equivalents.
    """
    url = f"{BASE_API_URL}/audit"
    logger.debug(f"\n{'=' * 200}\nMaking request to audit events from {url} for tenant {CONFIGS['tenant_name']}\n{'=' * 200}\n")
    logger.info(f"Making request to audit events api for tenant {CONFIGS['tenant_name']}")
    audit_request_response = get_response(url, headers)
    events = audit_request_response.get("events", [])
    links = audit_request_response.get("links", [])
    
    filtered_events = filter_by_date(events, from_date, to_date) if from_date or to_date else events
    filtered_links = filter_by_date(links, from_date, to_date) if from_date or to_date else links
    
    curl_equivalents_for_links = []
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        future_to_link = {executor.submit(fetch_events_from_link, link=link, headers=headers): link for link in filtered_links}
        for future in as_completed(future_to_link):
            try:
                events_result, curl_cmd = future.result()
                filtered_events.extend(events_result)
                curl_equivalents_for_links.append(curl_cmd)
            except Exception as e:
                logger.error(f"Error processing link {future_to_link[future]['url']}: {e}")
    
    logger.debug(f"Completed processing all links")
    curl_audit_request_equivalent = f"curl -X GET '{url}' -H 'Authorization: Bearer <token>'"
    filtered_events = add_formatted_date(filtered_events)
    filtered_links = add_formatted_date(filtered_links)
    
    return {
        "events": filtered_events, 
        "links": filtered_links, 
        "curl_audit_request_equivalent": curl_audit_request_equivalent, 
        "curl_equivalents_for_links": curl_equivalents_for_links
    }
