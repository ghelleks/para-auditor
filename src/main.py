"""Main entry point for PARA Auditor."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .config_manager import ConfigManager, ConfigError


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
            print("Please edit the configuration file with your API tokens and settings.")
            return 0
        
        # TODO: Implement OAuth setup flows here
        # This will be implemented in Phase 2
        logger.info("Configuration file already exists.")
        print("⚠️  OAuth setup not yet implemented. This will be available in Phase 2.")
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
        
        # TODO: Implement audit logic here
        # This will be implemented in Phase 3-5
        print("⚠️  Audit functionality not yet implemented.")
        print("This will be available in Phase 3-5 of development.")
        
        # Show what would be audited
        print("\n📊 Audit Configuration:")
        print(f"  • Todoist API: {'✅ Configured' if config_manager.todoist_token else '❌ Not configured'}")
        print(f"  • Work Domain: {config_manager.work_domain}")
        print(f"  • Personal Domain: {config_manager.personal_domain}")
        print(f"  • Projects Folder: {config_manager.projects_folder}")
        print(f"  • Areas Folder: {config_manager.areas_folder}")
        print(f"  • Similarity Threshold: {config_manager.similarity_threshold}")
        print(f"  • Report Format: {config_manager.report_format}")
        
        if args.work_only:
            print("  • Filter: Work items only")
        elif args.personal_only:
            print("  • Filter: Personal items only")
            
        if args.projects_only:
            print("  • Filter: Projects only")
        elif args.areas_only:
            print("  • Filter: Areas only")
        
        return 0
        
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        print(f"❌ Configuration error: {e}")
        print("💡 Run with --setup to create default configuration")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during audit: {e}")
        print(f"❌ Unexpected error: {e}")
        return 1


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