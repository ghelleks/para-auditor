# PARA Auditor

A Python tool for auditing consistency of PARA method organization across multiple productivity tools (Todoist, Apple Notes, Google Drive).

## Phase 1 - Foundation (COMPLETED)

✅ **Project Structure**: Complete directory structure with proper Python packaging  
✅ **Configuration System**: YAML-based configuration with validation and environment variable support  
✅ **Data Models**: PARAItem dataclass with full validation and utility methods  
✅ **CLI Framework**: Complete command-line interface with comprehensive options  
✅ **Package Setup**: Installation scripts, dependencies, and virtual environment support  

## Phase 2 - Authentication (COMPLETED)

✅ **Google OAuth**: Desktop application OAuth flow with multiple account support  
✅ **Todoist Authentication**: API token validation and connection testing  
✅ **Setup Command**: Interactive setup mode with step-by-step authentication  
✅ **Token Management**: Secure credential storage and automatic refresh  
✅ **Domain Validation**: Work vs personal account identification and validation  

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

```bash
# Create default configuration
python -m src.main --create-config

# Edit the configuration file with your API tokens
# config/config.yaml

# Run setup to authenticate with all services
python -m src.main --setup

# Run audit (Phase 3-5 - not yet implemented)
python -m src.main
```

### CLI Options

```bash
python -m src.main --help
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

## Development Status

- **Phase 1** ✅ Foundation (Complete)
- **Phase 2** ✅ Authentication (Complete)
- **Phase 3** ⏳ Data Collection (Not started) 
- **Phase 4** ⏳ Comparison Logic (Not started)
- **Phase 5** ⏳ Reporting (Not started)
- **Phase 6** ⏳ Testing & Polish (Not started)

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
python -m src.main --setup

# This will:
# - Validate Todoist connection
# - Authenticate work Google account
# - Authenticate personal Google account
# - Test all connections
```

## Next Steps

To continue development:

1. **Phase 3**: Add connectors for all three services (Todoist API, Google Drive API, AppleScript)
2. **Phase 4**: Implement comparison logic and inconsistency detection
3. **Phase 5**: Build comprehensive reporting system
4. **Phase 6**: Add tests and polish the user experience