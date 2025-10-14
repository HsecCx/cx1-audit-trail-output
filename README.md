# Checkmarx One Data Fetcher

Retrieves audit events and scan results from Checkmarx One API. Outputs data to CSV or Excel format with comprehensive field extraction and analysis capabilities.

## Features

- Retrieves audit events via a REST API
- Supports filtering events by date range (`--from_date` and `--to_date`). This is not necessary, if left blank it will search through all events.
- Supports mult-threading (`--thread_count`) with a minimum of 1 and maximum of 7. Defaults to 4 if not specified.
- Handles pagination via `links` field in the API response
- Outputs events to a `audit_events.csv` file
- Generates `curl` equivalents for debugging or replaying API calls

## Installation

1. Clone repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Create `config.json` in the root directory:

```json
{
    "api_url": "https://subdomain.ast.checkmarx.net/api",
    "iam_url": "https://subdomain.iam.checkmarx.net/auth/realms/",
    "api_key": "your-api-key-here",
    "tenant_name": "your-tenant-name"
}
```

## Usage

### Default Operation (Recommended)
Fetches both audit events and scan results for the last 30 days (including today) as Excel:
```bash
python run.py
```
OR
```bash
python audit_fetcher.py 
```
OR
```bash
python audit_fetcher.py --thread_count 2
```

### Custom Date Range
```bash
python run.py --from_date "01/01/2024" --to_date "03/01/2024"
```

### CSV Output
```bash
python run.py --output csv
```

### Custom Threading and Limits
```bash
python run.py --thread_count 6 --limit 2000 --offset 100
```

## Subcommands

### Audit Events Only
```bash
python run.py audit --from_date "01/01/2025" --to_date "02/01/2025"
python run.py audit --thread_count 6 --output csv
```

### Scan Results Only
```bash
python run.py scan --limit 500 --offset 0
python run.py scan --from_date "01/01/2024" --output excel
```

## Command Line Options

### Global Options
- `--from_date`: Start date (MM/DD/YY or MM/DD/YYYY format)
- `--to_date`: End date (MM/DD/YY or MM/DD/YYYY format)
- `--output`: Output format (`csv` or `excel`, default: `excel`)
- `--thread_count`: Number of threads (1-7, default: 4)
- `--limit`: Maximum scan results to return (default: 1000)
- `--offset`: Number of results to skip (default: 0)

### Audit Subcommand Options
- `--from_date`: Start date for audit events
- `--to_date`: End date for audit events
- `--thread_count`: Threading for audit API calls
- `--output`: Output format

### Scan Subcommand Options
- `--from_date`: Start date for scan results
- `--to_date`: End date for scan results
- `--limit`: Maximum results to return
- `--offset`: Results to skip
- `--output`: Output format

## Output Structure

### CSV Format
- `[tenant]_audit_events_[date_range].csv`: Audit events data
- `[tenant]_scan_results_[date_range].csv`: Scan results data

### Excel Format
Single file `[tenant]_cx1_data_[date_range].xlsx` with multiple worksheets:
- **Audit Events**: All audit trail data
- **Scans**: All scan results with data from all enabled engines (SAST, SCA, KICS, API Security, etc.)

## Extracted Data Fields

### Audit Events
- Standard audit fields plus extracted details from nested data structures
- Formatted dates and user information
- Action types and resource identifiers


## File Structure

```
cx1-audit-trail-output/
├── run.py                    # Main executable
├── objs/                     # Core modules
│   ├── __init__.py
│   ├── audit_fetcher.py      # Audit events handling
│   ├── scan_fetcher.py       # Scan results handling
│   └── output.py             # Output operations
├── utils/                    # Utility functions
│   ├── general.py
│   └── generate_oauth_token.py
├── config.json               # API configuration
├── requirements.txt
└── audit_events_output/      # Output directory
```

## Error Handling

### File Permission Errors
If Excel file is open in another program:
```
ERROR: Cannot save filename.xlsx
   - File may be open in Excel or another program
   - Close the file and try again
   - Or use --output csv as an alternative
```

### API Errors
- Invalid credentials: Check `config.json` values
- Network issues: Verify API URLs and connectivity
- Rate limiting: Tool automatically handles API throttling

### Date Format Errors
Accepted formats:
- `01/01/24`
- `01/01/2024` 
- `1/1/2024`

## Examples

### Basic Usage
```bash
# Default: Both audit and scan data, last 30 days (including today), Excel output
python run.py

# Custom date range with CSV output
python run.py --from_date "01/01/2024" --to_date "02/01/2024" --output csv

# High-performance collection
python run.py --thread_count 7 --limit 5000
```

### Targeted Collection
```bash
# Only audit events for specific period
python run.py audit --from_date "12/01/2024" --to_date "12/31/2024"

# Only recent scan results
python run.py scan --limit 100 --offset 0

# Large scan result collection
python run.py scan --limit 5000 --thread_count 6 --output csv
```

This will retrieve all audit events between May 1st and June 1st, 2024, and save them to `audit_events.csv`.
