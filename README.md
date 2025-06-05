# Audit Events Fetcher

This script retrieves audit events from a given API, supports date filtering, and outputs the result to a CSV file. It utilizes multithreading to fetch additional paginated results efficiently.

## Features

- Retrieves audit events via a REST API
- Supports filtering events by date range (`--from_date` and `--to_date`). This is not necessary, if left blank it will search through all events.
- Supports mult-threading (`--thread_count`) with a minimum of 1 and maximum of 7. Defaults to 4 if not specified.
- Handles pagination via `links` field in the API response
- Outputs events to a `audit_events.csv` file
- Generates `curl` equivalents for debugging or replaying API calls

## Requirements

- Python 3.7+
- Required Python packages: `requests`, `concurrent.futures` (included in standard library)
```
pip install -r requirements.txt
```

## Usage

```bash
python audit_fetcher.py --from_date 01/01/2024 --to_date 06/01/2024
```
OR
```bash
python audit_fetcher.py 
```
OR
```bash
python audit_fetcher.py --thread_count 2
```

Dates must be in either `MM/DD/YY` or `MM/DD/YYYY` format.

## Configuration

Ensure `utils/generate_oauth_token.py` contains the following methods:

- `generate_oauth_token(configs)` - Generates a valid OAuth token.
- `load_config()` - Loads configuration including `api_url`.

The configuration must include:

```json
{
    "api_url": "https://<subdomain>.ast.checkmarx.net/api",
    "iam_url": "https:/<subdomain>.iam.checkmarx.net/auth/realms/",
    "api_key": "<apikey>",
    "tenant_name": "<tenant_name>"
}
```

## Output

- A file named `audit_events.csv` containing the event details.
- Curl commands for each API call, useful for debugging.

## File Structure

```
.
├── audit_fetcher.py
├── utils/
│   ├── generate_oauth_token.py
│   └── general.py
├── config.json
├── requirements.txt
├── audit_events_outputs
```

## Logging

Logs will be printed to the console to show progress, errors, and links being processed.



## Example

```bash
python audit_fetcher.py --from_date 05/01/2024 --to_date 06/01/2024
```

This will retrieve all audit events between May 1st and June 1st, 2024, and save them to `audit_events.csv`.
