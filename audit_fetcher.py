import requests
from utils.generate_oauth_token import generate_oauth_token,load_config
from utils.general import AuditUtils
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from datetime import datetime
import argparse
from typing import Union, List, Optional
from dateutil.parser import isoparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIGS = load_config()
BASE_API_URL = CONFIGS["api_url"]

def get_response(url: str,headers: dict) -> dict:
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

def get_audit_events(headers: dict,from_date: Optional[str]=None,to_date: Optional[str]=None,thread_count: Optional[int]=4) -> dict:
    """
    Retrieves and filters audit events from the Audit API.

    This function makes an initial request to the audit endpoint, retrieves the main set of events,
    and uses multithreading to fetch additional events from pagination links. Optionally filters
    events by a specified date range.

    Args:
        headers (dict): HTTP headers including Authorization token.
        from_date (str, optional): Start date for filtering events (format: MM/DD/YY or MM/DD/YYYY). Defaults to None.
        to_date (str, optional): End date for filtering events (format: MM/DD/YY or MM/DD/YYYY). Defaults to None.
        thread_count (int, optional): Number of threads to use when fetching paginated events. Defaults to 4.

    Returns:
        dict: A dictionary containing:
            - "events": List of filtered audit events.
            - "links": Pagination links that were followed.
            - "curl_audit_request_equivalent": Curl command for the initial API call.
            - "curl_equivalents_for_links": List of curl commands for paginated requests.
    """
    url = f"{BASE_API_URL}/audit"
    logger.info(f"Making request to audit events from {url}")
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
                print(f"Error processing link {future_to_link[future]['url']}: {e}")
    logger.info(f"Completed processing all links")
    curl_audit_request_equivalent = f"curl -X GET '{url}' -H 'Authorization: Bearer <token>'"
    filtered_events = add_formatted_date(filtered_events)
    filtered_links = add_formatted_date(filtered_links)
    return {"events":filtered_events, "links":filtered_links, "curl_audit_request_equivalent":curl_audit_request_equivalent, "curl_equivalents_for_links":curl_equivalents_for_links}

def add_formatted_date(items: list, fmt: str = "%m/%d/%Y %H:%M") -> list:
    """
    Adds a formatted, Excel-friendly date string to each audit event in the list.

    Parses the 'eventDate' field of each item (ISO 8601 format) and adds a new field
    'FormattedEventDate' using the specified format string.

    Args:
        items (list): A list of dictionaries, each containing an 'eventDate' key.
        fmt (str, optional): A datetime format string to apply. Defaults to "%m/%d/%Y %H:%M".

    Returns:
        list: The modified list of dictionaries, each now containing a 'FormattedEventDate' field.
    """
    for item in items:
        try:
            # Parse ISO 8601 format with Z
            parsed_dt = isoparse(item["eventDate"])
            item["FormattedEventDate"] = parsed_dt.strftime(fmt)
            # Compare only date portion
        except Exception as e:
            logging.error(f"Error adding formatted datetime to item: {item}. Error: {e}")
    return items

def filter_by_date(events:list, from_date:str, to_date:str) -> List[dict]:
    """
    Filters a list of audit events based on a date range.

    This function parses the 'eventDate' field of each event, compares it against the provided
    `from_date` and `to_date`, and returns only those events that fall within the range. The
    comparison is based on the date portion (not time).

    Args:
        events (list): A list of dictionaries, each representing an audit event with an 'eventDate' field in ISO 8601 format.
        from_date (str): Start date as a string in MM/DD/YY or MM/DD/YYYY format. Events before this date are excluded.
        to_date (str): End date as a string in MM/DD/YY or MM/DD/YYYY format. Events after this date are excluded.

    Returns:
        list: A list of audit events that fall within the specified date range.
    """
    
    from_dt = parse_flexible_date(from_date) if from_date else None
    to_dt = parse_flexible_date(to_date) if to_date else None
    filtered_events = []
    for event in events:
        try:
            # Parse ISO 8601 format with Z
            event_dt = isoparse(event["eventDate"])
            # Compare only date portion
            if (
                (from_dt is None or event_dt.date() >= from_dt.date()) and
                (to_dt is None or event_dt.date() <= to_dt.date())
            ):
                filtered_events.append(event)
        except Exception as e:
            logger.error(f"Error filtering by date: {e}")
            continue

    return filtered_events

def parse_flexible_date(date_str: str) -> datetime:
    """
    Parses a date string in either MM/DD/YYYY or MM/DD/YY format into a datetime object.

    Attempts to parse the input string using common U.S. date formats. If the input does not
    match any supported format, a ValueError is raised.

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


def fetch_events_from_link(headers:dict, link:dict) -> tuple:
    """
    Fetches audit events from a given pagination link.

    Makes a GET request to the specified link's URL using the provided headers.
    Also generates a curl equivalent command for debugging or replaying the request.

    Args:
        headers (dict): HTTP headers including the Authorization token.
        link (dict): A dictionary containing the 'url' key pointing to the API endpoint.

    Returns:
        tuple: A tuple containing:
            - events_result (dict): The JSON response from the API.
            - curl_cmd (str): A curl command string that replicates the GET request.
    """
    link_url = link["url"]
    logger.info(f"Processing link {link_url}")
    events_result = get_response(link_url, headers)
    curl_cmd = f"curl -X GET '{link_url}' -H 'Authorization: Bearer <token>'"
    return events_result, curl_cmd

def restricted_int_threads(val: Union[int,str]) -> int:
    """
    Validates that the provided value is an integer between 1 and 7 (inclusive).

    Intended for use as a custom `type` function in argparse to enforce bounds on thread count.

    Args:
        val (str): The input value from the command-line argument (will be cast to int).

    Returns:
        int: The validated integer value.

    Raises:
        argparse.ArgumentTypeError: If the value is not an integer or not within the range 1 to 7.
    """
    ival = int(val)
    if ival < 1 or ival > 7:
        raise argparse.ArgumentTypeError("Thread count must be between 1 and 7.")
    return ival

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and filter audit events.")
    parser.add_argument("--from_date", type=str, help="Start date in MM/DD/YY or MM/DD/YYYY format", default=None)
    parser.add_argument("--to_date", type=str, help="End date in MM/DD/YY or MM/DD/YYYY format", default=None)
    parser.add_argument("--thread_count", type=restricted_int_threads, help="Number of threads to use for fetching audit events. must be between 1 and 7", default=4)

    args = parser.parse_args()
    oauth_token = generate_oauth_token(CONFIGS)
    if not oauth_token or "Error" in oauth_token:
        logger.error("Failed to generate OAuth token.")
        exit(1)
    else:
        headers = {"Authorization": f"Bearer {oauth_token}", "Content-Type": "application/json"}
        audit_event_results = get_audit_events(headers, from_date=args.from_date, to_date=args.to_date, thread_count=args.thread_count)
        # audit_event_results = get_audit_events(headers, from_date="01/01/2025", to_date="02/10/2025", thread_count=1)
        events = audit_event_results["events"]
        sorted_events = sorted(events, key=lambda x: x["FormattedEventDate"])
        audit_utils = AuditUtils().write_json_list_to_csv(sorted_events, "audit_events.csv")