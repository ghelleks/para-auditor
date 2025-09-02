"""Main entry point for PARA Auditor."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .auditor.comparator import ItemComparator
from .auditor.report_generator import ReportGenerator
from .auth.google_auth import GoogleAuthenticator, GoogleAuthError
from .auth.todoist_auth import TodoistAuthenticator
from .config_manager import ConfigError, ConfigManager
from .connectors.apple_notes_connector import AppleNotesConnector
from .connectors.gdrive_connector import GDriveConnector
from .connectors.todoist_connector import TodoistConnector
from .models.para_item import CategoryType, ItemSource, ItemType, PARAItem
from .utils.spinner import spinner


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    log_level = logging.DEBUG if verbose else logging.WARNING
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

    # Set our own module loggers to WARNING unless verbose
    if not verbose:
        logging.getLogger('__main__').setLevel(logging.WARNING)
        logging.getLogger('src.auth.todoist_auth').setLevel(logging.WARNING)
        logging.getLogger('src.auth.google_auth').setLevel(logging.WARNING)
        logging.getLogger('src.connectors.todoist_connector').setLevel(logging.WARNING)
        logging.getLogger('src.connectors.gdrive_connector').setLevel(logging.WARNING)
        logging.getLogger('src.connectors.apple_notes_connector').setLevel(logging.WARNING)
        logging.getLogger('src.auditor.comparator').setLevel(logging.WARNING)


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

    # Area display options
    parser.add_argument(
        '--show-all-areas',
        action='store_true',
        help='Show all PARA areas in the report (default: only show areas missing next actions)'
    )

    # Next action options
    parser.add_argument(
        '--next-action-label',
        type=str,
        metavar='LABEL',
        help='Label name to check for next actions (default: "next"). "@" prefix optional.'
    )
    parser.add_argument(
        '--skip-next-actions',
        action='store_true',
        help='Skip checking for next action labels'
    )

    # Output control options
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed progress information'
    )
    output_group.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='No output until completion (silent mode)'
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

        work_secrets_path = Path(config_manager.work_client_secrets_path)
        personal_secrets_path = Path(config_manager.personal_client_secrets_path)

        if not work_secrets_path.exists() or not personal_secrets_path.exists():
            print("❌ Google OAuth client secrets files not found")
            print("\nTo set up Google Drive access, you need OAuth credentials for work and personal accounts:")
            print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
            print("2. Create a new project or select existing")
            print("3. Enable Google Drive API")
            print("4. Create OAuth 2.0 credentials (Desktop application)")
            print("5. Download the credentials and save as:")
            print(f"   • Work account: {work_secrets_path}")
            print(f"   • Personal account: {personal_secrets_path}")
            print("\nNote: You can use the same OAuth credentials for both accounts")
            print("      if they're from the same Google Cloud project.")
            print("\nTip: You can customize these paths in config/config.yaml")
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


def collect_all_data_verbose(config_manager: ConfigManager, args: argparse.Namespace, google_auth: GoogleAuthenticator) -> List[PARAItem]:
    """Collect data with verbose progress output."""
    all_items = []

    print("📥 Collecting data from sources...")

    # Collect from Todoist
    if not args.dry_run:
        print("  • Fetching Todoist projects...")

        # Determine next action label (CLI override takes precedence)
        next_action_label = config_manager.next_action_label
        if hasattr(args, 'next_action_label') and args.next_action_label:
            next_action_label = args.next_action_label

        # Skip next actions if requested
        if hasattr(args, 'skip_next_actions') and args.skip_next_actions:
            print("    Skipping next action checks as requested")
            next_action_label = None  # This will disable next action checking

        todoist_connector = TodoistConnector(
            config_manager.todoist_token,
            next_action_label=next_action_label or "next"
        )
        todoist_items = todoist_connector.get_projects()
        all_items.extend(todoist_items)

        # Show next action info if enabled
        if next_action_label and not (hasattr(args, 'skip_next_actions') and args.skip_next_actions):
            print(f"    Found {len(todoist_items)} Todoist projects (checking @{next_action_label} labels)")
        else:
            print(f"    Found {len(todoist_items)} Todoist projects")

    # Collect from Google Drive (Work)
    if not args.dry_run:
        print("  • Fetching work Google Drive folders...")
        work_credentials = google_auth.get_credentials('work')
        work_connector = GDriveConnector(work_credentials, 'work')
        work_items = work_connector.get_para_folders(config_manager.gdrive_base_folder_name)
        all_items.extend(work_items)
        print(f"    Found {len(work_items)} work folders")

    # Collect from Google Drive (Personal)
    if not args.dry_run:
        print("  • Fetching personal Google Drive folders...")
        personal_credentials = google_auth.get_credentials('personal')
        personal_connector = GDriveConnector(personal_credentials, 'personal')
        personal_items = personal_connector.get_para_folders(config_manager.gdrive_base_folder_name)
        all_items.extend(personal_items)
        print(f"    Found {len(personal_items)} personal folders")

    # Collect from Apple Notes
    if not args.dry_run:
        print("  • Fetching Apple Notes folders...")
        notes_connector = AppleNotesConnector()
        notes_items = notes_connector.get_para_folders()
        all_items.extend(notes_items)
        print(f"    Found {len(notes_items)} Apple Notes folders")

    return all_items


def collect_all_data_silent(config_manager: ConfigManager, args: argparse.Namespace, google_auth: GoogleAuthenticator) -> List[PARAItem]:
    """Collect data silently (no console output)."""
    all_items = []

    # Collect from Todoist
    if not args.dry_run:
        # Determine next action label (CLI override takes precedence)
        next_action_label = config_manager.next_action_label
        if hasattr(args, 'next_action_label') and args.next_action_label:
            next_action_label = args.next_action_label

        # Skip next actions if requested
        if hasattr(args, 'skip_next_actions') and args.skip_next_actions:
            next_action_label = None  # This will disable next action checking

        todoist_connector = TodoistConnector(
            config_manager.todoist_token,
            next_action_label=next_action_label or "next"
        )
        todoist_items = todoist_connector.get_projects()
        all_items.extend(todoist_items)

    # Collect from Google Drive (Work)
    if not args.dry_run:
        work_credentials = google_auth.get_credentials('work')
        work_connector = GDriveConnector(work_credentials, 'work')
        work_items = work_connector.get_para_folders(config_manager.gdrive_base_folder_name)
        all_items.extend(work_items)

    # Collect from Google Drive (Personal)
    if not args.dry_run:
        personal_credentials = google_auth.get_credentials('personal')
        personal_connector = GDriveConnector(personal_credentials, 'personal')
        personal_items = personal_connector.get_para_folders(config_manager.gdrive_base_folder_name)
        all_items.extend(personal_items)

    # Collect from Apple Notes
    if not args.dry_run:
        notes_connector = AppleNotesConnector()
        notes_items = notes_connector.get_para_folders()
        all_items.extend(notes_items)

    return all_items


def compare_items_verbose(filtered_items: List[PARAItem], args: argparse.Namespace):
    """Compare items with verbose output."""
    print(f"\n📊 Analyzing {len(filtered_items)} items...")
    comparator = ItemComparator(
        similarity_threshold=args.threshold,
        strict_mode=False
    )
    return comparator.compare_items(filtered_items)


def compare_items_silent(filtered_items: List[PARAItem], args: argparse.Namespace):
    """Compare items silently."""
    comparator = ItemComparator(
        similarity_threshold=args.threshold,
        strict_mode=False
    )
    return comparator.compare_items(filtered_items)


def handle_audit_mode(config_manager: ConfigManager, args: argparse.Namespace) -> int:
    """Handle audit mode with three output modes: default (animation), quiet, or verbose."""
    logger = logging.getLogger(__name__)

    # Determine output mode early for error handling
    verbose_mode = args.verbose
    quiet_mode = args.quiet
    animation_mode = not verbose_mode and not quiet_mode  # Default

    try:
        # Load and validate configuration
        config_manager.load_config()
        logger.info("Configuration loaded successfully")

        # Initialize authenticators for status checking
        google_auth = GoogleAuthenticator(config_manager)
        todoist_auth = TodoistAuthenticator(config_manager)

        # Authentication check (only in verbose mode)
        if verbose_mode:
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
        else:
            # Silent authentication check
            todoist_valid = todoist_auth.test_connection()
            work_auth = google_auth.is_authenticated('work')
            personal_auth = google_auth.is_authenticated('personal')

        if not (todoist_valid and work_auth and personal_auth):
            print("❌ Authentication check failed")
            print("The following services need attention:")

            # Provide detailed Todoist reason if available
            if not todoist_valid:
                details = {}
                try:
                    details = todoist_auth.validate_connection_detailed() or {}
                except Exception:
                    details = {}

                if not details.get('token_configured', True):
                    print("  • Todoist: API token not configured")
                elif details.get('token_configured') and not details.get('token_valid', False):
                    print("  • Todoist: API token is invalid")
                elif details.get('error'):
                    print(f"  • Todoist: {details.get('error')}")
                else:
                    print("  • Todoist: Not connected")

                # Verbose-mode setup reminders for Todoist
                if verbose_mode:
                    print("    - Add your token to config.yaml under todoist.api_token")
                    print("    - Get the token from Todoist Settings → Integrations")
                    print("    - Then run: para-auditor --setup")

            # Google Drive account-specific status
            if not work_auth:
                print("  • Work Google Drive: Not authenticated")
                if verbose_mode:
                    print("    - Ensure OAuth client secrets exist at:")
                    print(f"      {config_manager.work_client_secrets_path}")
                    print("    - In Google Cloud Console, enable Drive API and create Desktop OAuth credentials")
                    print("    - Then run: para-auditor --setup and sign in with your work account domain")
            if not personal_auth:
                print("  • Personal Google Drive: Not authenticated")
                if verbose_mode:
                    print("    - Ensure OAuth client secrets exist at:")
                    print(f"      {config_manager.personal_client_secrets_path}")
                    print("    - In Google Cloud Console, enable Drive API and create Desktop OAuth credentials")
                    print("    - Then run: para-auditor --setup and sign in with your personal account")

            print("\n💡 Run 'para-auditor --setup' to configure authentication")
            return 1

        # Data collection with appropriate output mode
        if verbose_mode:
            print("\n🔍 Starting PARA Audit...")
            print("-" * 23)
            all_items = collect_all_data_verbose(config_manager, args, google_auth)
        elif quiet_mode:
            all_items = collect_all_data_silent(config_manager, args, google_auth)
        else:  # animation_mode (default)
            with spinner("🔄 Auditing PARA organization"):
                all_items = collect_all_data_silent(config_manager, args, google_auth)

        # Apply filters
        filtered_items = apply_filters(all_items, args)

        if args.dry_run:
            if verbose_mode:
                print("🔍 Dry run mode - showing configuration only")
                print_audit_configuration(config_manager, args)
            return 0

        # Analysis phase
        if verbose_mode:
            comparison_result = compare_items_verbose(filtered_items, args)
        elif animation_mode:
            with spinner("📊 Analyzing items"):
                comparison_result = compare_items_silent(filtered_items, args)
        else:  # quiet_mode
            comparison_result = compare_items_silent(filtered_items, args)

        # Generate report (all modes)
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
            metadata_overrides=metadata_overrides,
            show_all_areas=args.show_all_areas
        )

        # Output report
        if not args.output:
            print("\n" + "="*60)
            print(report_content)
        else:
            if not quiet_mode:
                print(f"\n✅ Report saved to: {args.output}")

        # Summary (verbose mode only)
        if verbose_mode:
            print_audit_summary(comparison_result)

        return 0

    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        print(f"❌ Configuration error: {e}")
        print("💡 Run with --setup to create default configuration")
        return 1
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        print(f"❌ Audit failed: {e}")
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

    # Show next action configuration
    next_action_label = config_manager.next_action_label
    if hasattr(args, 'next_action_label') and args.next_action_label:
        next_action_label = args.next_action_label
        print(f"  • Next Action Label: @{next_action_label} (CLI override)")
    elif hasattr(args, 'skip_next_actions') and args.skip_next_actions:
        print("  • Next Action Check: Disabled (CLI override)")
    else:
        print(f"  • Next Action Label: @{next_action_label}")

    if args.work_only:
        print("  • Filter: Work items only")
    elif args.personal_only:
        print("  • Filter: Personal items only")

    if args.projects_only:
        print("  • Filter: Projects only")
    elif args.areas_only:
        print("  • Filter: Areas only")

    # Show all areas option
    if args.show_all_areas:
        print("  • Show All Areas: Yes")
    else:
        print("  • Show All Areas: No (default)")


def print_project_alignment_view(all_items: List[PARAItem], comparison_result) -> None:
    """Print project-by-project alignment view."""
    # Get all Todoist projects as the primary source
    todoist_items = [item for item in all_items if item.source == ItemSource.TODOIST]

    if not todoist_items:
        print("No Todoist projects found to display alignment for.")
        return

    print("📋 PROJECT ALIGNMENT OVERVIEW")
    print("=" * 40)
    print()

    for todoist_item in sorted(todoist_items, key=lambda x: x.name.lower()):
        # Find matching items in other sources
        matching_items = find_matching_items_for_project(todoist_item, all_items, comparison_result)

        # Display project info
        status_emoji = "✅" if todoist_item.is_active else "⭕"
        category_emoji = "🏢" if todoist_item.category == CategoryType.WORK else "🏠"

        print(f"{status_emoji} {category_emoji} {todoist_item.raw_name or todoist_item.name}")

        # Get all unique issues for this project
        all_issues = get_project_issues(todoist_item, matching_items, comparison_result)

        if all_issues:
            for issue in all_issues:
                print(f"  • {issue}")
        else:
            print("  ✅ All systems aligned")

        print()  # Empty line between projects


def find_matching_items_for_project(todoist_item: PARAItem, all_items: List[PARAItem], comparison_result) -> Dict[ItemSource, List[PARAItem]]:
    """Find matching items for a Todoist project across all sources."""
    matching_items = {source: [] for source in ItemSource}

    # Look through item groups to find matches
    for group in comparison_result.item_groups:
        if todoist_item in group:
            for item in group:
                if item.source != ItemSource.TODOIST:
                    matching_items[item.source].append(item)
            break

    return matching_items


def get_project_issues(todoist_item: PARAItem, matching_items: Dict[ItemSource, List[PARAItem]], comparison_result) -> List[str]:
    """Get all unique issues for a specific Todoist project."""
    issues = set()  # Use set to avoid duplicates

    # Determine which sources to check based on project category
    if todoist_item.category == CategoryType.WORK:
        expected_sources = [ItemSource.GDRIVE_WORK, ItemSource.APPLE_NOTES]
    else:  # Personal project
        expected_sources = [ItemSource.GDRIVE_PERSONAL, ItemSource.APPLE_NOTES]

    # Check for missing folders
    for source in expected_sources:
        matches = matching_items.get(source, [])
        if not matches:
            source_name = "Work Google Drive" if source == ItemSource.GDRIVE_WORK else \
                         "Personal Google Drive" if source == ItemSource.GDRIVE_PERSONAL else \
                         "Apple Notes"
            issues.add(f"❌ Missing in {source_name}: Create folder '{todoist_item.name}'")

    # Check for inconsistencies involving this project
    seen_descriptions = set()  # Track unique issue descriptions
    for inconsistency in comparison_result.inconsistencies:
        if todoist_item in inconsistency.items:
            # Only include if it affects our expected sources
            sources_in_inconsistency = {item.source for item in inconsistency.items}
            if any(source in expected_sources for source in sources_in_inconsistency):
                # Clean up the description and make it more actionable
                description = inconsistency.description
                if description not in seen_descriptions:
                    seen_descriptions.add(description)
                    issue_type = inconsistency.type.value.replace('_', ' ').title()
                    issues.add(f"⚠️  {issue_type}: {description}")

    return sorted(list(issues))  # Sort for consistent output


def print_audit_summary(result) -> None:
    """Print audit summary to console."""
    print("\n📈 Audit Summary:")
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
