"""Main entry point for PARA Auditor."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, List

from .config_manager import ConfigManager, ConfigError
from .auth.google_auth import GoogleAuthenticator, GoogleAuthError
from .auth.todoist_auth import TodoistAuthenticator, TodoistAuthError
from .connectors.todoist_connector import TodoistConnector
from .connectors.gdrive_connector import GDriveConnector
from .connectors.apple_notes_connector import AppleNotesConnector
from .auditor.comparator import ItemComparator
from .auditor.report_generator import ReportGenerator
from .models.para_item import PARAItem, ItemType, CategoryType


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('para_auditor.log')
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)
    logging.getLogger('google_auth_httplib2').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog='para-auditor',
        description='Audit consistency of PARA method organization across multiple tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  para-auditor                    # Run full audit
  para-auditor --setup            # Initialize OAuth flows
  para-auditor --config custom.yaml  # Use custom config file
  para-auditor --format json     # Output in JSON format
  para-auditor --verbose         # Enable debug logging
        """
    )
    
    # Main operation modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--setup',
        action='store_true',
        help='Initialize OAuth flows and create default configuration'
    )
    mode_group.add_argument(
        '--audit',
        action='store_true',
        default=True,
        help='Run audit (default mode)'
    )
    
    # Configuration options
    parser.add_argument(
        '--config',
        type=str,
        metavar='PATH',
        help='Path to configuration file (default: config/config.yaml)'
    )
    parser.add_argument(
        '--create-config',
        action='store_true',
        help='Create default configuration file and exit'
    )
    
    # Output options
    parser.add_argument(
        '--format',
        choices=['markdown', 'json', 'text'],
        default='markdown',
        help='Report output format (default: markdown)'
    )
    parser.add_argument(
        '--output',
        type=str,
        metavar='PATH',
        help='Output file path (default: stdout)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        metavar='FLOAT',
        default=0.8,
        help='Name similarity threshold (0.0-1.0, default: 0.8)'
    )
    
    # Filtering options
    parser.add_argument(
        '--work-only',
        action='store_true',
        help='Audit only work-related items'
    )
    parser.add_argument(
        '--personal-only',
        action='store_true',
        help='Audit only personal items'
    )
    parser.add_argument(
        '--projects-only',
        action='store_true',
        help='Audit only projects (active items)'
    )
    parser.add_argument(
        '--areas-only',
        action='store_true',
        help='Audit only areas (inactive items)'
    )
    
    # Debugging options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be audited without making API calls'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )
    
    return parser


def handle_setup_mode(config_manager: ConfigManager) -> int:
    """Handle setup mode operations."""
    logger = logging.getLogger(__name__)
    
    try:
        # Create default config if it doesn't exist
        if not config_manager.config_path.exists():
            logger.info("Creating default configuration file...")
            config_manager.create_default_config()
            print(f"✅ Default configuration created at: {config_manager.config_path}")
            print("Please edit the configuration file with your API tokens and settings before running setup again.")
            return 0
        
        print("🔧 PARA Auditor Setup")
        print("====================")
        
        # Load configuration
        try:
            config_manager.load_config()
        except ConfigError as e:
            print(f"❌ Configuration error: {e}")
            print("Please fix your configuration file and try again.")
            return 1
        
        # Initialize authenticators
        google_auth = GoogleAuthenticator(config_manager)
        todoist_auth = TodoistAuthenticator(config_manager)
        
        # Step 1: Validate Todoist connection
        print("\n📋 Step 1: Validating Todoist Connection")
        print("-" * 40)
        
        todoist_result = todoist_auth.validate_connection_detailed()
        
        if not todoist_result['token_configured']:
            print("❌ Todoist API token not configured")
            print(todoist_auth.get_token_instructions())
            return 1
        elif not todoist_result['token_valid']:
            print("❌ Todoist API token is invalid")
            print("Please check your token in the configuration file.")
            print(todoist_auth.get_token_instructions())
            return 1
        else:
            print("✅ Todoist API connection successful")
            user_info = todoist_result.get('user_info', {})
            if user_info:
                print(f"   Projects found: {user_info.get('project_count', 'Unknown')}")
        
        # Step 2: Setup Google OAuth for work account
        print("\n🏢 Step 2: Setting up Work Google Account")
        print("-" * 42)
        
        work_domain = config_manager.work_domain
        print(f"Expected work domain: {work_domain}")
        
        if not Path("config/client_secrets.json").exists():
            print("❌ Google OAuth client secrets file not found")
            print("\nTo set up Google Drive access:")
            print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
            print("2. Create a new project or select existing")
            print("3. Enable Google Drive API")
            print("4. Create OAuth 2.0 credentials (Desktop application)")
            print("5. Download as 'client_secrets.json' and place in config/ directory")
            return 1
        
        try:
            if not google_auth.is_authenticated('work'):
                print("Setting up work account authentication...")
                google_auth.authenticate_account('work')
            else:
                print("✅ Work account already authenticated")
                
            # Test work account connection
            if google_auth.test_connection('work'):
                print("✅ Work Google Drive connection successful")
                work_info = google_auth.get_account_info('work')
                if 'email' in work_info:
                    print(f"   Account: {work_info['email']}")
            else:
                print("❌ Work Google Drive connection failed")
                return 1
                
        except GoogleAuthError as e:
            print(f"❌ Work account setup failed: {e}")
            return 1
        
        # Step 3: Setup Google OAuth for personal account
        print("\n🏠 Step 3: Setting up Personal Google Account")
        print("-" * 45)
        
        personal_domain = config_manager.personal_domain
        print(f"Expected personal domain: {personal_domain}")
        
        try:
            if not google_auth.is_authenticated('personal'):
                print("Setting up personal account authentication...")
                google_auth.authenticate_account('personal')
            else:
                print("✅ Personal account already authenticated")
                
            # Test personal account connection
            if google_auth.test_connection('personal'):
                print("✅ Personal Google Drive connection successful")
                personal_info = google_auth.get_account_info('personal')
                if 'email' in personal_info:
                    print(f"   Account: {personal_info['email']}")
            else:
                print("❌ Personal Google Drive connection failed")
                return 1
                
        except GoogleAuthError as e:
            print(f"❌ Personal account setup failed: {e}")
            return 1
        
        # Step 4: Final validation
        print("\n✅ Step 4: Setup Complete!")
        print("-" * 25)
        print("All services are now authenticated and ready.")
        print("You can now run: para-auditor")
        
        return 0
        
    except ConfigError as e:
        logger.error(f"Setup failed: {e}")
        print(f"❌ Setup failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during setup: {e}")
        print(f"❌ Unexpected error: {e}")
        return 1


def handle_audit_mode(config_manager: ConfigManager, args: argparse.Namespace) -> int:
    """Handle audit mode operations."""
    logger = logging.getLogger(__name__)
    
    try:
        # Load and validate configuration
        config_manager.load_config()
        logger.info("Configuration loaded successfully")
        
        # Initialize authenticators for status checking
        google_auth = GoogleAuthenticator(config_manager)
        todoist_auth = TodoistAuthenticator(config_manager)
        
        # Check authentication status
        print("🔐 Authentication Status:")
        print("-" * 25)
        
        # Todoist status
        todoist_valid = todoist_auth.test_connection()
        print(f"  • Todoist API: {'✅ Connected' if todoist_valid else '❌ Not connected'}")
        
        # Google Drive status
        work_auth = google_auth.is_authenticated('work')
        personal_auth = google_auth.is_authenticated('personal')
        print(f"  • Work Google Drive: {'✅ Authenticated' if work_auth else '❌ Not authenticated'}")
        print(f"  • Personal Google Drive: {'✅ Authenticated' if personal_auth else '❌ Not authenticated'}")
        
        if not (todoist_valid and work_auth and personal_auth):
            print("\n⚠️  Some services are not properly authenticated.")
            print("💡 Run 'para-auditor --setup' to configure authentication")
            return 1
        
        # Run the audit
        print("\n🔍 Starting PARA Audit...")
        print("-" * 23)
        
        try:
            # Collect data from all sources
            print("📥 Collecting data from sources...")
            all_items = []
            
            # Collect from Todoist
            if not args.dry_run:
                print("  • Fetching Todoist projects...")
                todoist_connector = TodoistConnector(
                    config_manager.todoist_token,
                    work_domains=[config_manager.work_domain],
                    personal_domains=[config_manager.personal_domain]
                )
                todoist_items = todoist_connector.get_projects()
                all_items.extend(todoist_items)
                print(f"    Found {len(todoist_items)} Todoist projects")
            
            # Collect from Google Drive (Work)
            if not args.dry_run:
                print("  • Fetching work Google Drive folders...")
                work_credentials = google_auth.get_credentials('work')
                work_connector = GDriveConnector(work_credentials, 'work')
                work_items = work_connector.get_para_folders()
                all_items.extend(work_items)
                print(f"    Found {len(work_items)} work folders")
            
            # Collect from Google Drive (Personal)
            if not args.dry_run:
                print("  • Fetching personal Google Drive folders...")
                personal_credentials = google_auth.get_credentials('personal')
                personal_connector = GDriveConnector(personal_credentials, 'personal')
                personal_items = personal_connector.get_para_folders()
                all_items.extend(personal_items)
                print(f"    Found {len(personal_items)} personal folders")
            
            # Collect from Apple Notes
            if not args.dry_run:
                print("  • Fetching Apple Notes folders...")
                notes_connector = AppleNotesConnector()
                notes_items = notes_connector.get_para_folders()
                all_items.extend(notes_items)
                print(f"    Found {len(notes_items)} Apple Notes folders")
            
            # Apply filters
            filtered_items = apply_filters(all_items, args)
            
            if args.dry_run:
                print("🔍 Dry run mode - showing configuration only")
                print_audit_configuration(config_manager, args)
                return 0
            
            print(f"\n📊 Analyzing {len(filtered_items)} items...")
            
            # Compare items and find inconsistencies
            comparator = ItemComparator(
                similarity_threshold=args.threshold,
                strict_mode=False
            )
            comparison_result = comparator.compare_items(filtered_items)
            
            # Generate report
            report_generator = ReportGenerator()
            
            # Determine output format
            output_format = getattr(args, 'format', 'markdown')
            
            # Generate metadata
            metadata_overrides = {
                'filters_applied': {
                    'work_only': args.work_only,
                    'personal_only': args.personal_only,
                    'projects_only': args.projects_only,
                    'areas_only': args.areas_only,
                    'threshold': args.threshold
                }
            }
            
            # Generate and output report
            report_content = report_generator.generate_report(
                result=comparison_result,
                format_type=output_format,
                output_path=args.output,
                metadata_overrides=metadata_overrides
            )
            
            # Print to console if no output file specified
            if not args.output:
                print("\n" + "="*60)
                print(report_content)
            else:
                print(f"\n✅ Report saved to: {args.output}")
            
            # Print summary
            print_audit_summary(comparison_result)
            
            return 0
            
        except Exception as e:
            logger.error(f"Audit failed: {e}")
            print(f"❌ Audit failed: {e}")
            return 1
        
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        print(f"❌ Configuration error: {e}")
        print("💡 Run with --setup to create default configuration")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during audit: {e}")
        print(f"❌ Unexpected error: {e}")
        return 1


def apply_filters(items: List[PARAItem], args: argparse.Namespace) -> List[PARAItem]:
    """Apply command-line filters to items."""
    filtered_items = items
    
    # Filter by category
    if args.work_only:
        filtered_items = [item for item in filtered_items if item.category == CategoryType.WORK]
    elif args.personal_only:
        filtered_items = [item for item in filtered_items if item.category == CategoryType.PERSONAL]
    
    # Filter by type
    if args.projects_only:
        filtered_items = [item for item in filtered_items if item.type == ItemType.PROJECT]
    elif args.areas_only:
        filtered_items = [item for item in filtered_items if item.type == ItemType.AREA]
    
    return filtered_items


def print_audit_configuration(config_manager: ConfigManager, args: argparse.Namespace) -> None:
    """Print audit configuration for dry run mode."""
    print("\n📊 Audit Configuration:")
    print(f"  • Work Domain: {config_manager.work_domain}")
    print(f"  • Personal Domain: {config_manager.personal_domain}")
    print(f"  • Projects Folder: {config_manager.projects_folder}")
    print(f"  • Areas Folder: {config_manager.areas_folder}")
    print(f"  • Similarity Threshold: {args.threshold}")
    print(f"  • Report Format: {getattr(args, 'format', 'markdown')}")
    
    if args.work_only:
        print("  • Filter: Work items only")
    elif args.personal_only:
        print("  • Filter: Personal items only")
        
    if args.projects_only:
        print("  • Filter: Projects only")
    elif args.areas_only:
        print("  • Filter: Areas only")


def print_audit_summary(result) -> None:
    """Print audit summary to console."""
    print(f"\n📈 Audit Summary:")
    print(f"  • Consistency Score: {result.consistency_score:.1%}")
    print(f"  • Total Items: {result.total_items}")
    print(f"  • Consistent Items: {result.consistent_items}")
    print(f"  • Issues Found: {len(result.inconsistencies)}")
    
    if result.inconsistencies:
        print(f"    - High Priority: {result.high_severity_count}")
        print(f"    - Medium Priority: {result.medium_severity_count}")
        print(f"    - Low Priority: {result.low_severity_count}")
    
    if result.consistency_score >= 0.9:
        print("  🎉 Excellent consistency!")
    elif result.consistency_score >= 0.7:
        print("  👍 Good consistency with room for improvement")
    else:
        print("  ⚠️  Significant inconsistencies detected")


def main(argv: Optional[list] = None) -> int:
    """Main entry point for the application."""
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Set up logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    logger.info("PARA Auditor starting")
    
    try:
        # Handle create-config mode
        if args.create_config:
            config_manager = ConfigManager(args.config)
            config_manager.create_default_config(force=False)
            print(f"✅ Default configuration created at: {config_manager.config_path}")
            return 0
        
        # Validate threshold
        if not 0.0 <= args.threshold <= 1.0:
            print("❌ Threshold must be between 0.0 and 1.0")
            return 1
        
        # Initialize config manager
        config_manager = ConfigManager(args.config)
        
        # Handle different modes
        if args.setup:
            return handle_setup_mode(config_manager)
        else:
            # Default to audit mode
            return handle_audit_mode(config_manager, args)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        print("\n⚠️  Operation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())