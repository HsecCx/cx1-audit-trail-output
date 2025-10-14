#!/usr/bin/env python3
"""
Checkmarx One Data Fetcher - Main Executable

A unified command-line tool for fetching audit events and scan results 
from the Checkmarx One API with support for various output formats.

Usage:
    python run.py audit [options]     # Fetch audit events
    python run.py scan [options]      # Fetch scan results
    python run.py --help              # Show help
"""

import argparse
import logging
import sys
from typing import Union

from utils.generate_oauth_token import generate_oauth_token, load_config
from objs.audit_fetcher import get_audit_events
from objs.scan_fetcher import get_scan_results
from objs.output import OutputManager

logger = logging.getLogger(__name__)


def restricted_int_threads(val: Union[int, str]) -> int:
    """Validates thread count is between 1 and 7."""
    ival = int(val)
    if ival < 1 or ival > 7:
        raise argparse.ArgumentTypeError("Thread count must be between 1 and 7.")
    return ival


def create_audit_parser(subparsers):
    """Create argument parser for audit commands."""
    audit_parser = subparsers.add_parser(
        'audit', 
        help='Fetch audit events',
        description='Fetch and export audit events from Checkmarx One'
    )
    
    audit_parser.add_argument(
        "--from_date", 
        type=str, 
        help="Start date in MM/DD/YY or MM/DD/YYYY format", 
        default=None
    )
    audit_parser.add_argument(
        "--to_date", 
        type=str, 
        help="End date in MM/DD/YY or MM/DD/YYYY format", 
        default=None
    )
    audit_parser.add_argument(
        "--thread_count", 
        type=restricted_int_threads, 
        help="Number of threads for concurrent operations (1-7)", 
        default=4
    )
    audit_parser.add_argument(
        "--output", 
        type=str, 
        choices=["csv", "excel"], 
        help="Output format", 
        default="excel"
    )
    audit_parser.add_argument("--debug", action="store_true", help="Enable debug logging", default=False)
    
    return audit_parser


def create_scan_parser(subparsers):
    """Create argument parser for scan commands."""
    scan_parser = subparsers.add_parser(
        'scan', 
        help='Fetch scan results',
        description='Fetch and export scan results from Checkmarx One'
    )
    
    scan_parser.add_argument(
        "--from_date", 
        type=str, 
        help="Start date in MM/DD/YY or MM/DD/YYYY format", 
        default=None
    )
    scan_parser.add_argument(
        "--to_date", 
        type=str, 
        help="End date in MM/DD/YY or MM/DD/YYYY format", 
        default=None
    )
    scan_parser.add_argument(
        "--limit", 
        type=int, 
        help="Maximum number of scan results to return", 
        default=100
    )
    scan_parser.add_argument(
        "--offset", 
        type=int, 
        help="Number of results to skip", 
        default=0
    )
    scan_parser.add_argument(
        "--output", 
        type=str, 
        choices=["csv", "excel"], 
        help="Output format", 
        default="excel"
    )
    scan_parser.add_argument("--debug", action="store_true", help="Enable debug logging", default=False)
    
    return scan_parser


def initialize_api() -> tuple:
    """Initialize API configuration and authentication."""
    try:
        configs = load_config()
        oauth_token = generate_oauth_token(configs)
        
        if not oauth_token or "Error" in oauth_token:
            logger.error("Failed to generate OAuth token.")
            return None, None
        
        headers = {
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Successfully authenticated for tenant: {configs['tenant_name']}")
        return configs, headers
        
    except Exception as e:
        logger.error(f"API initialization failed: {e}")
        return None, None


def handle_audit_command(args) -> int:
    """Handle audit events fetching."""
    logger.info("FETCHING AUDIT EVENTS")
    logger.info("=" * 50)
    
    configs, headers = initialize_api()
    if not headers:
        return 1
    
    try:
        # Fetch audit events
        audit_results = get_audit_events(
            headers, 
            from_date=args.from_date, 
            to_date=args.to_date, 
            thread_count=args.thread_count
        )
        
        events = audit_results["events"]
        sorted_events = sorted(events, key=lambda x: x.get("FormattedEventDate", ""))
        
        # Save results
        output_manager = OutputManager(tenant_name=configs['tenant_name'])
        success = output_manager.save_audit_events(sorted_events, args.output)
        
        if success:
            logger.info(f"Successfully saved {len(sorted_events)} audit events")
            return 0
        else:
            logger.error("Failed to save audit events")
            return 1
            
    except Exception as e:
        logger.error(f"Error fetching audit events: {e}")
        return 1


def handle_scan_command(args) -> int:
    """Handle scan results fetching."""
    logger.info("FETCHING SCAN RESULTS")
    logger.info("=" * 50)
    
    configs, headers = initialize_api()
    if not headers:
        return 1
    
    try:
        # Fetch scan results
        scan_results = get_scan_results(
            headers, 
            from_date=args.from_date,
            to_date=args.to_date,
            limit=args.limit,
            offset=args.offset
        )
        
        if "error" in scan_results:
            logger.error(f"Failed to fetch scan results: {scan_results['error']}")
            return 1
        
        scans = scan_results["scans"]
        
        # Log sample data structure for debugging
        if scans:
            logger.debug(f"Sample scan fields: {list(scans[0].keys())}")
        
        # Save results
        output_manager = OutputManager(tenant_name=configs['tenant_name'])
        success = output_manager.save_scan_results(
            scans, 
            args.output, 
            limit=args.limit, 
            offset=args.offset
        )
        
        if success:
            logger.info(f"Successfully saved {len(scans)} scan results")
            return 0
        else:
            logger.error("Failed to save scan results")
            return 1
            
    except Exception as e:
        logger.error(f"Error fetching scan results: {e}")
        return 1


def get_default_date_range() -> tuple:
    """Get default date range (last 30 days including today)."""
    from datetime import datetime, timedelta
    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)
    return (
        thirty_days_ago.strftime("%m/%d/%Y"),
        today.strftime("%m/%d/%Y")
    )

def handle_both_command(args) -> int:
    """Handle both audit and scan data fetching."""
    logger.info("FETCHING BOTH AUDIT EVENTS AND SCAN RESULTS")
    logger.info("=" * 60)
    
    configs, headers = initialize_api()
    if not headers:
        return 1
    
    # Use default date range if not specified
    from_date = args.from_date
    to_date = args.to_date
    
    if not from_date and not to_date:
        from_date, to_date = get_default_date_range()
        logger.info(f"Using default 30-day window (including today): {from_date} to {to_date}")
    
    try:
        # Fetch audit events
        logger.info("Fetching audit events...")
        audit_results = get_audit_events(headers, from_date=from_date, to_date=to_date, thread_count=args.thread_count)
        audit_events = audit_results["events"]
        sorted_audit_events = sorted(audit_events, key=lambda x: x.get("FormattedEventDate", ""))
        
        # Fetch scan results
        logger.info("Fetching scan results...")
        scan_results = get_scan_results(headers, from_date=from_date, to_date=to_date, limit=args.limit, offset=args.offset)
        
        if "error" in scan_results:
            logger.error(f"Failed to fetch scan results: {scan_results['error']}")
            return 1
        
        scan_events = scan_results["scans"]
        
        # Debug: Log scan data structure
        if scan_events:
            logger.debug(f"Sample scan fields: {list(scan_events[0].keys())}")
            logger.debug(f"Sample scan data: {scan_events[0]}")
        
        # Save results
        output_manager = OutputManager(tenant_name=configs['tenant_name'])
        success = output_manager.save_combined_data(sorted_audit_events, scan_events, args.output, from_date, to_date)
        
        if success:
            logger.info(f"Successfully saved {len(sorted_audit_events)} audit events and {len(scan_events)} scan results")
            return 0
        else:
            logger.error("Failed to save combined data")
            return 1
            
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return 1

def main() -> int:
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="Checkmarx One Data Fetcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                                    # Fetch both (default: last 30 days including today)
  python run.py --from_date "01/01/2024" --output excel
  python run.py audit --from_date "01/01/2024" --to_date "03/01/2024"
  python run.py scan --limit 500 --offset 100
        """
    )
    
    # Add arguments for default "both" mode
    parser.add_argument("--from_date", type=str, help="Start date in MM/DD/YY or MM/DD/YYYY format", default=None)
    parser.add_argument("--to_date", type=str, help="End date in MM/DD/YY or MM/DD/YYYY format", default=None)
    parser.add_argument("--thread_count", type=restricted_int_threads, help="Number of threads for concurrent operations (1-7)", default=4)
    parser.add_argument("--output", type=str, choices=["csv", "excel"], help="Output format", default="excel")
    parser.add_argument("--limit", type=int, help="Maximum number of scan results to return", default=1000)
    parser.add_argument("--offset", type=int, help="Number of results to skip", default=0)
    parser.add_argument("--debug", action="store_true", help="Enable debug logging", default=False)
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands (optional - defaults to both)')
    
    # Create subcommand parsers
    create_audit_parser(subparsers)
    create_scan_parser(subparsers)
    
    args = parser.parse_args()
    
    # Configure logging based on debug flag
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Default to both if no command specified
    if not args.command:
        return handle_both_command(args)
    
    # Route to appropriate handler
    if args.command == 'audit':
        return handle_audit_command(args)
    elif args.command == 'scan':
        return handle_scan_command(args)
    else:
        logger.error(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
