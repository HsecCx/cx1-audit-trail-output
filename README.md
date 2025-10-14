# Checkmarx One Data Fetcher

Retrieves audit events and scan results from Checkmarx One API. Outputs data to CSV or Excel format with comprehensive field extraction and analysis capabilities.

## Features

- **Combined Data Collection**: Fetches both audit events and scan results in a single operation
- **Flexible Date Filtering**: Supports MM/DD/YY and MM/DD/YYYY formats with RFC3339 API filtering
- **Multiple Output Formats**: CSV (separate files) or Excel (multi-worksheet)
- **Advanced Excel Output**: Separate worksheets per scan engine with extracted metadata fields
- **Multithreading**: Configurable thread count (1-7) for efficient API calls
- **Smart Defaults**: Last 30 days (including today) when no dates specified
- **Error Handling**: Graceful handling of file permissions and API errors

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

### Analysis Scenarios
```bash
# Monthly security report
python run.py --from_date "11/01/2024" --to_date "11/30/2024" --output excel

# Troubleshoot recent scan issues
python run.py scan --limit 50 --output excel

# Full historical collection
python run.py --from_date "01/01/2024" --thread_count 7 --limit 10000
```

## Troubleshooting

### Common Issues

**No data returned**: 
- Verify date range contains activity
- Check API permissions for audit and scan endpoints
- Confirm tenant configuration

**Excel save failures**:
- Close Excel files before running
- Check write permissions in output directory
- Use `--output csv` as alternative

**API authentication errors**:
- Verify `api_key` in `config.json`
- Check `iam_url` and `api_url` are correct for your environment
- Ensure API key has required permissions

**Performance issues**:
- Reduce `--limit` for scan results
- Lower `--thread_count` if API throttling occurs
- Use CSV output for very large datasets

### Debug Mode
Add debug logging by examining the console output for:
- Sample scan fields and data structure
- API request URLs being called
- Progress indicators for threading operations

## Output File Naming

Files are automatically named with your tenant name and date ranges when specified:
- `[tenant]_cx1_data_01-01-2024_to_02-01-2024.xlsx`
- `[tenant]_audit_events_01-01-2024_to_02-01-2024.csv`
- `[tenant]_scan_results_01-01-2024_to_02-01-2024.csv`

Without date ranges:
- `[tenant]_cx1_data.xlsx`
- `[tenant]_audit_events.csv`
- `[tenant]_scan_results.csv`

*Note: `[tenant]` is replaced with your actual tenant name from config.json*
