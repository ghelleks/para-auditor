# PARA Auditor

A Python tool for auditing consistency of PARA method organization across multiple productivity tools (Todoist, Apple Notes, Google Drive).

## Features

- **Multi-Platform Integration**: Connects to Todoist, Google Drive, and Apple Notes
- **PARA Method Support**: Identifies Projects (active) and Areas (inactive) across tools
- **Intelligent Matching**: Advanced fuzzy string matching with normalization
- **Inconsistency Detection**: 9 types of issues including missing items, status mismatches, and account placement errors
- **Emoji Analysis**: Detects and suggests appropriate emojis with extensive keyword mappings
- **Work/Personal Classification**: Automatically categorizes items and validates account placement
- **Multiple Usage Options**: Direct script, pip installation, or Python module execution

## Quick Start

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

**Option 1: Direct script (no installation required)**
```bash
# Create default configuration
./para-auditor --create-config

# Edit the configuration file with your API tokens
# config/config.yaml

# Run setup to authenticate with all services
./para-auditor --setup

# Run full audit
./para-auditor
```

**Option 2: Install as package**
```bash
# Install in development mode
pip install -e .

# Now you can use para-auditor from anywhere
para-auditor --create-config
para-auditor --setup
para-auditor
```

### CLI Options

```bash
para-auditor --help
```

Key options:
- `--setup`: Initialize OAuth flows and configuration
- `--create-config`: Generate default configuration file
- `--format {markdown,json,text}`: Report output format
- `--work-only` / `--personal-only`: Filter by category
- `--projects-only` / `--areas-only`: Filter by type
- `--verbose`: Enable debug logging

## Project Structure

```
para_auditor/
├── config/                       # Configuration files
│   ├── config.yaml               # Main configuration (created by user)
│   ├── config.yaml.template      # Template configuration
│   └── credentials/              # OAuth tokens (auto-generated)
├── src/                          # Source code
│   ├── main.py                   # CLI entry point
│   ├── config_manager.py         # Configuration handling
│   ├── auth/                     # Authentication modules
│   ├── connectors/               # API integrations
│   ├── models/                   # Data models
│   │   └── para_item.py          # Core PARAItem model
│   ├── auditor/                  # Audit logic
│   └── utils/                    # Utilities
├── tests/                        # Test modules
├── scripts/applescript/          # AppleScript integration
├── requirements.txt              # Python dependencies
└── setup.py                     # Package installation
```

## Configuration

The tool uses a YAML configuration file at `config/config.yaml`:

```yaml
todoist:
  api_token: "your_todoist_token_here"

google_drive:
  work_account_domain: "@yourcompany.com"
  personal_account_domain: "@gmail.com"
  scopes:
    - "https://www.googleapis.com/auth/drive.readonly"
    - "https://www.googleapis.com/auth/drive.metadata.readonly"

apple_notes:
  projects_folder: "Projects"
  areas_folder: "Areas"

audit_settings:
  similarity_threshold: 0.8
  report_format: "markdown"
```

## Current Status

PARA Auditor is currently in active development. Core data collection and comparison logic are implemented. The reporting system is the next major component to be completed.

## System Requirements

- **macOS** (required for Apple Notes integration)
- **Python 3.8+**
- Internet connection for OAuth and API calls

## Authentication Setup

### Prerequisites

1. **Todoist API Token**:
   - Go to [Todoist Settings → Integrations](https://todoist.com/prefs/integrations)
   - Copy your API token from the Developer section
   - Add it to `config/config.yaml`

2. **Google Cloud Setup**:
   - Create project at [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Google Drive API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download as `client_secrets.json` and place in `config/` directory

### Setup Process

```bash
# 1. Configure your tokens in config.yaml
# 2. Run interactive setup
para-auditor --setup

# This will:
# - Validate Todoist connection
# - Authenticate work Google account
# - Authenticate personal Google account
# - Test all connections
```

## Contributing

This project is in active development. Key areas for contribution include:

- Report generation and formatting
- Additional test coverage
- Documentation improvements
- Additional productivity tool integrations