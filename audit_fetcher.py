import requests
from utils.generate_oauth_token import generate_oauth_token,load_config
from utils.general import AuditUtils
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from datetime import datetime
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIGS = load_config()
BASE_API_URL = CONFIGS["api_url"]

def get_response(url,headers):
    """
    Helper function to make a GET request to the specified URL with the provided headers.

    Args:
        url (str): The URL to send the GET request to.
        headers (dict): The headers to include in the request.

    Returns:
        dict: The JSON response from the API.
    """
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return {"Error": f"Request failed with status code {response.status_code}"}

def get_audit_events(headers: dict,from_date=None,to_date=None,thread_count=4):
    """
    Retrieves audit events from the Audit API.

    Returns:
        dict: The JSON response from the API.
    """
    url = f"{BASE_API_URL}/audit"
    logger.info(f"Making request to audit events from {url}")
    audit_request_response = get_response(url, headers)
    events = audit_request_response["events"]
    links = audit_request_response["links"]
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
    return {"events":filtered_events, "links":filtered_links, "curl_audit_request_equivalent":curl_audit_request_equivalent, "curl_equivalents_for_links":curl_equivalents_for_links}

def filter_by_date(events:list, from_date:str, to_date:str):
    from_dt = parse_flexible_date(from_date) if from_date else None
    to_dt = parse_flexible_date(to_date) if to_date else None
    filtered_events = []
    for event in events:
        try:
            # Parse ISO 8601 format with Z
            event_dt = datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
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

def parse_flexible_date(date_str):
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Date '{date_str}' is not in MM/DD/YY or MM/DD/YYYY format.")


def fetch_events_from_link(headers:dict, link:dict):
    link_url = link["url"]
    logger.info(f"Processing link {link_url}")
    events_result = get_response(link_url, headers)
    curl_cmd = f"curl -X GET '{link_url}' -H 'Authorization: Bearer <token>'"
    return events_result, curl_cmd

def restricted_int_threads(val):
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
    if "Error" not in oauth_token:
        headers = {"Authorization": f"Bearer {oauth_token}", "Content-Type": "application/json"}
        audit_event_results = get_audit_events(headers, from_date=args.from_date, to_date=args.to_date, thread_count=args.thread_count)
        events = audit_event_results["events"]
        audit_utils = AuditUtils().write_json_list_to_csv(events, "audit_events.csv")
