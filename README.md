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
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
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
# Interactive setup for all services
./para-auditor --setup
```

### 4. Run Audit
```bash
# Run full audit
./para-auditor

# Or with detailed output
./para-auditor --verbose
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
- **Python 3.8+**
- **API Access**: Todoist API token, Google OAuth credentials

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