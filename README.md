# PARA Auditor

Keep your PARA method organization consistent across Todoist, Google Drive, and Apple Notes.

## What It Does

PARA Auditor checks that your projects and areas are properly aligned across your productivity tools. It identifies missing folders, status inconsistencies, and naming variations so you can maintain a clean, organized PARA system.

**Key Features:**
- **Work/Personal Classification**: Use 💼 emoji prefix in Todoist for work projects  
- **Cross-Platform Sync**: Audits Todoist, Google Drive (work & personal), and Apple Notes
- **Smart Matching**: Finds similar items even with slight name variations
- **Category-Specific Checking**: Work projects only check work accounts, personal projects only check personal accounts

## Quick Start

### 1. Install Dependencies

**Using uv (recommended):**
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

**Using pip (legacy):**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt.bak
```

### 2. Setup Configuration
```bash
# Create default config file
./para-auditor --create-config

# Edit config/config.yaml with your API tokens
# - Add Todoist API token
# - Set your work/personal email domains  
# - Configure Google OAuth credentials
```

### 3. Authenticate Services
```bash
# Interactive setup for all services (uv)
uv run python -m src.main --setup
# or using the script
./para-auditor --setup
```

### 4. Run Audit
```bash
# Run full audit (uv)
uv run python -m src.main --audit
# or using the script
./para-auditor --audit

# Or with detailed output
uv run python -m src.main --audit --verbose
# or using the script
./para-auditor --audit --verbose
```

## How It Works

1. **Todoist**: Processes favorited projects. Work projects start with 💼 emoji.
2. **Google Drive**: Scans your `@2-Areas` folder in both work and personal accounts
3. **Apple Notes**: Checks `Projects` and `Areas` folders
4. **Analysis**: Matches items by name and reports inconsistencies

## Example Output

```
📋 PROJECT ALIGNMENT OVERVIEW
========================================

✅ 🏢 💼RHEL Cloud
  • ⚠️  Status Mismatch: active in Todoist but inactive in Google Drive
  • ❌ Missing in Apple Notes: Create folder 'RHEL Cloud'

✅ 🏠 🏝️ Summer 2025
  ✅ All systems aligned
```

## Requirements

- **macOS** (for Apple Notes integration)
- **Python 3.9+** (3.8 supported with legacy pip install)
- **uv** (recommended package manager) or pip
- **API Access**: Todoist API token, Google OAuth credentials

## Development

### Using uv (recommended)

```bash
# Setup development environment
uv sync --extra dev

# Run tests
uv run pytest

# Format code
uv run black src tests
uv run ruff format src tests

# Run linting
uv run ruff check src tests
uv run mypy src

# Run all checks
uv run ruff check src tests && uv run mypy src && uv run pytest

# Clean build artifacts (use dev script)
./scripts/dev.sh clean

# Update dependencies
uv lock
uv sync

# Build package
uv build
```

### Development Scripts

The most standard approach with uv is to use direct commands or the development helper script:

```bash
# Use the development helper script
./scripts/dev.sh setup    # Initial setup
./scripts/dev.sh run --help  # Run with args
./scripts/dev.sh test     # Run tests
./scripts/dev.sh lint     # Run linting
./scripts/dev.sh format   # Format code
./scripts/dev.sh check    # Run all checks
./scripts/dev.sh clean    # Clean build artifacts
```

### Direct uv Commands

| Command | Description |
|---------|-------------|
| `uv run pytest` | Run tests |
| `uv run ruff check src tests` | Check code style |
| `uv run mypy src` | Type checking |
| `uv run black src tests` | Format code |
| `uv run python -m src.main --audit` | Run PARA audit |
| `uv run python -m src.main --setup` | Setup API configuration |

## Configuration

Minimal `config/config.yaml`:
```yaml
todoist:
  api_token: "your_todoist_token_here"

google_drive:
  work_account_domain: "@yourcompany.com"
  personal_account_domain: "@gmail.com"
  work_client_secrets: "config/credentials/work_client_secrets.json"
  personal_client_secrets: "config/credentials/personal_client_secrets.json"

apple_notes:
  projects_folder: "Projects"
  areas_folder: "Areas"
```

Get your Todoist token from [Settings → Integrations](https://todoist.com/prefs/integrations). Set up Google OAuth at [Google Cloud Console](https://console.cloud.google.com/) (enable Drive API, create Desktop OAuth credentials).