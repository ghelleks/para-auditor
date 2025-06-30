# PARA Auditor

A Python tool for auditing consistency of PARA method organization across multiple productivity tools (Todoist, Apple Notes, Google Drive).

## Phase 1 - Foundation (COMPLETED)

✅ **Project Structure**: Complete directory structure with proper Python packaging  
✅ **Configuration System**: YAML-based configuration with validation and environment variable support  
✅ **Data Models**: PARAItem dataclass with full validation and utility methods  
✅ **CLI Framework**: Complete command-line interface with comprehensive options  
✅ **Package Setup**: Installation scripts, dependencies, and virtual environment support  

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

# Edit the configuration file
# config/config.yaml

# Run setup (Phase 2 - not yet implemented)
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
- **Phase 2** ⏳ Authentication (Not started)
- **Phase 3** ⏳ Data Collection (Not started) 
- **Phase 4** ⏳ Comparison Logic (Not started)
- **Phase 5** ⏳ Reporting (Not started)
- **Phase 6** ⏳ Testing & Polish (Not started)

## System Requirements

- **macOS** (required for Apple Notes integration)
- **Python 3.8+**
- Internet connection for OAuth and API calls

## Next Steps

To continue development:

1. **Phase 2**: Implement Google OAuth flows and Todoist authentication
2. **Phase 3**: Add connectors for all three services (Todoist API, Google Drive API, AppleScript)
3. **Phase 4**: Implement comparison logic and inconsistency detection
4. **Phase 5**: Build comprehensive reporting system
5. **Phase 6**: Add tests and polish the user experience