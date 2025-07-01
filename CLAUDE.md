# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PARA Auditor is a Python tool that audits consistency of PARA method organization across multiple productivity tools (Todoist, Apple Notes, Google Drive). It identifies discrepancies between how projects and areas are organized across these platforms.

## Key Architecture

### Core Data Model
- `PARAItem`: Central data structure representing projects/areas with properties:
  - `name`: Project/area name
  - `type`: "Project" or "Area" 
  - `is_active`: Boolean (favorited/starred status)
  - `category`: "work" or "personal"
  - `source`: Tool origin (todoist, apple_notes, gdrive_personal, gdrive_work)

### Module Structure
- `src/connectors/`: API integrations for each tool (Todoist API, Google Drive API, AppleScript for Apple Notes)
- `src/auth/`: Authentication handling (Google OAuth for multiple accounts, Todoist API tokens)
- `src/auditor/`: Core comparison logic, emoji suggestion, report generation
- `src/models/`: Data models and validation
- `src/utils/`: Name matching, URL parsing utilities

### Authentication Requirements
- **Google Drive**: OAuth2 flow for both work and personal accounts with separate token storage
- **Todoist**: API token from user settings
- **Apple Notes**: AppleScript execution (macOS only)

## Development Commands

### Setup
```bash
pip install -r requirements.txt
python para_auditor.py --setup  # Initial OAuth flows
```

### Running
```bash
python para_auditor.py  # Full audit
```

### Testing
```bash
python -m pytest tests/
```

## Configuration

### Main Config (`config/config.yaml`)
- Todoist API token
- Google account domains for work/personal classification
- Apple Notes folder names
- Audit settings (similarity thresholds, report format)

### Authentication Storage
- `config/credentials/work_drive_token.pickle`
- `config/credentials/personal_drive_token.pickle`
- `config/client_secrets.json` (user-provided Google OAuth credentials)

## Key Implementation Details

### PARA Classification Rules
- **Active (Project)**: Favorited in Todoist, Starred in Google Drive, In Apple Notes "Projects" folder
- **Inactive (Area)**: Not favorited in Todoist, Not starred in Google Drive, In Apple Notes "Areas" folder

### Work/Personal Detection
- **Work projects**: Those starting with 💼 emoji in their name
- **Personal projects**: All other projects (default)
- Work items → work Google Drive account only
- Personal items → personal Google Drive account only

### Audit Types
1. Missing items across tools
2. Status inconsistencies (active/inactive conflicts)
3. Wrong Google Drive account placement
4. Naming variations and duplicates
5. Missing Google Drive links in Todoist
6. Missing emoji prefixes

## Platform Requirements
- **macOS required** for Apple Notes integration via AppleScript
- Python 3.8+
- Internet connectivity for OAuth and API calls

## API Integration Notes

### Google Drive API
- Focuses on "2-@Area" directory structure
- Handles pagination and rate limits
- Supports multiple account authentication

### Todoist API  
- Processes only favorited projects (active projects in PARA method)
- Classifies work vs personal based on 💼 emoji prefix in project names
- Extracts Google Drive links from task content for folder linking

### Apple Notes AppleScript
- Uses custom AppleScript to extract folder structures
- Handles "Projects" and "Areas" folder hierarchies