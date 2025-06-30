# PARA Auditor - Requirements Document

## Overview
Create a Python script that audits consistency of PARA method organization across multiple tools and identifies discrepancies.

## Current System Architecture

### Tools Used
1. **Todoist**
   - Projects created for each PARA Area
   - "Favorite" status indicates active Project (vs Area)
   - API available

2. **Apple Notes**
   - "Projects" folder contains Project subfolders
   - "Areas" folder contains Area subfolders  
   - No official API - requires AppleScript automation

3. **Google Drive (Personal)**
   - All folders in "2-@Area" directory
   - Star status indicates Project (vs Area)
   - API available

4. **Google Drive (Work)**
   - Same structure as personal
   - Separate authentication required
   - API available

## Data Model

### PARA Item Structure
```
PARAItem:
  - name: string
  - type: "Project" | "Area"
  - is_active: boolean (favorited/starred)
  - category: "work" | "personal"
  - source: "todoist" | "apple_notes" | "gdrive_personal" | "gdrive_work"
```

## System Rules (Clarified)

### 1. Project vs Area Classification
- **Active = Project**: Favorited in Todoist, Starred in Google Drive, Located in "Projects" folder in Apple Notes
- **Inactive = Area**: Not favorited in Todoist, Not starred in Google Drive, Located in "Areas" folder in Apple Notes

### 2. Work vs Personal Classification
- **Todoist & Apple Notes**: Mixed work and personal items (no distinction)
- **Google Drive**: Work items go to work account, personal items go to personal account
- **No Cross-Account Duplication**: Work items should NOT appear in personal Google Drive and vice versa

### 3. Work/Personal Detection
- **Challenge**: Todoist has no naming convention to distinguish work vs personal
- **Potential Solution**: Some Todoist projects contain Google Drive links as tasks - could parse these to determine account
- **Fallback**: May need manual classification or heuristics

### 4. Consistency Rules
Expected consistency across tools:
- **Active Status**: If favorited in Todoist → should be starred in corresponding Google Drive AND in Apple Notes "Projects" folder
- **Inactive Status**: If not favorited in Todoist → should not be starred in Google Drive AND should be in Apple Notes "Areas" folder
- **Existence**: Every item should exist in Todoist, Apple Notes, and the appropriate Google Drive (work OR personal, not both)

## Technical Considerations

## Technical Considerations

### Authentication & Configuration
- **Todoist**: API token (stored in config file or environment variable)
- **Google Drive**: OAuth2 flow for both work and personal accounts
- **Apple Notes**: Local AppleScript execution (no auth required)

### Google OAuth Setup
1. Create Google Cloud project
2. Enable Google Drive API
3. Create OAuth 2.0 credentials (Desktop application type)
4. Download `client_secrets.json`
5. First run will open browser for authorization
6. Subsequent runs use saved refresh tokens

### Configuration Files Structure
```
para_auditor/
├── config/
│   ├── client_secrets.json          # Google OAuth credentials
│   ├── config.yaml                  # Main configuration
│   └── credentials/                 # Auto-generated token storage
│       ├── work_drive_token.pickle
│       └── personal_drive_token.pickle
├── para_auditor.py                  # Main script
├── requirements.txt                 # Python dependencies
└── README.md                       # Setup instructions
```

### Sample config.yaml
```yaml
todoist:
  api_token: "your_todoist_token_here"
  
google_drive:
  work_account_domain: "@yourcompany.com"  # Help identify work vs personal
  personal_account_domain: "@gmail.com"
  scopes:
    - "https://www.googleapis.com/auth/drive.readonly"
    - "https://www.googleapis.com/auth/drive.metadata.readonly"
  
apple_notes:
  projects_folder: "Projects"
  areas_folder: "Areas"
  
audit_settings:
  similarity_threshold: 0.8  # For detecting similar names
  report_format: "markdown"  # or "json", "text"
```

## Output Requirements

### Report Format
What should the audit report include?
- Missing items per tool?
- Conflicting active status?
- Potential duplicates?
- Summary statistics?

### Action Items
Should the script:
- Just report issues?
- Suggest specific actions?
- Provide commands to fix issues?

## Audit Types

### 1. Missing Google Drive Links
- Todoist projects without any Google Drive links
- Requires manual resolution

### 2. Missing Items
- Items in one tool but not others
- Example: "Website Redesign" exists in Todoist and Apple Notes but not in corresponding Google Drive

### 3. Status Inconsistencies  
- Items with conflicting active/inactive status across tools
- Example: "Marketing Plan" is favorited in Todoist but in Apple Notes "Areas" folder

### 4. Wrong Google Drive Account
- Todoist project links to work account but folder found in personal account (or vice versa)

### 5. Naming Variations
- Similar names that might be the same item
- Example: "Website Redesign" vs "Website-Redesign" vs "Site Redesign"

### 6. Link-Folder Mismatches
- Google Drive link in Todoist points to folder that doesn't exist
- Or points to different folder name than the project name

### 7. Missing Emojis
- Project/Area names that don't begin with an emoji
- Tool should suggest appropriate emoji based on project name/category

## Emoji Suggestion Logic

### Detection
- Check if project/area name starts with an emoji character
- Use Unicode emoji detection to identify emoji at start of string

### Suggestion Algorithm
Suggest emojis based on:
1. **Keyword matching**: Common project types (website → 🌐, marketing → 📱, finance → 💰)
2. **Category patterns**: Work vs personal context
3. **Common PARA categories**: Health (🏃), Home (🏠), Career (💼), Learning (📚)

### Implementation Notes
- Create emoji mapping dictionary with keywords → suggested emojis
- Allow multiple suggestions per project
- Consider context clues from project description or Google Drive folder structure

## Dependencies

### Python Packages
```
google-auth>=2.0.0
google-auth-oauthlib>=0.7.0
google-api-python-client>=2.0.0
requests>=2.28.0
PyYAML>=6.0
```

### System Requirements
- macOS (for AppleScript integration)
- Python 3.8+
- Internet connection for OAuth flow and API calls

## Example Output

```
PARA AUDITOR REPORT
Generated: 2025-06-30 14:30:00
==================================================

SUMMARY
- 23 total projects/areas found in Todoist
- 8 inconsistencies detected
- 3 items missing emoji prefixes

==================================================

🚨 CRITICAL ISSUES

Missing Google Drive Links (2 items)
- "Website Redesign" - No Google Drive link found in tasks
- "Home Renovation" - No Google Drive link found in tasks

==================================================

📍 MISSING ITEMS

Items in Todoist but not in Apple Notes (1 item)
- "🎯 Q1 Planning" (favorited) - Should be in Apple Notes "Projects" folder

Items in Todoist but not in Google Drive (2 items)
- "🏠 Home Renovation" (not favorited) - Should be in Personal Google Drive (not starred)
- "📱 Mobile App" (favorited) - Should be in Work Google Drive (starred)

Items in Apple Notes but not in Todoist (1 item)
- "Garden Planning" (in Areas folder) - Should be added to Todoist as non-favorited project

==================================================

⚠️  STATUS CONFLICTS

Active/Inactive Mismatches (2 items)
- "🌐 Website Redesign" 
  ✅ Todoist: Favorited (Project)
  ❌ Apple Notes: In "Areas" folder (should be in "Projects")
  ❌ Work Google Drive: Not starred (should be starred)

- "💰 Budget Planning"
  ❌ Todoist: Not favorited (Area) 
  ❌ Apple Notes: In "Projects" folder (should be in "Areas")
  ✅ Personal Google Drive: Not starred (correct)

==================================================

🔍 POTENTIAL DUPLICATES

Similar Names Found
- "Website Redesign" vs "Website-Redesign" (85% match)
  - Todoist: "Website Redesign" 
  - Work Google Drive: "Website-Redesign"
  
==================================================

😀 MISSING EMOJIS

Projects/Areas Without Emoji Prefixes (3 items)
- "Website Redesign" → Suggested: 🌐 🖥️ 💻
- "Marketing Campaign" → Suggested: 📱 📊 🎯  
- "Kitchen Remodel" → Suggested: 🏠 🔨 🏗️

==================================================

✅ ALL GOOD

These items are properly synchronized:
- 🎯 Q1 Planning (Work Project)
- 🏃 Fitness Goals (Personal Area) 
- 📚 Learning Python (Personal Project)
- 💼 Team Management (Work Area)

==================================================

RECOMMENDATIONS
1. Add Google Drive links to 2 projects marked as CRITICAL
2. Create missing folders/notes for 4 items  
3. Update active/inactive status for 2 items with conflicts
4. Consider renaming "Website-Redesign" to match "Website Redesign"
5. Add emoji prefixes to 3 items
```

### Work/Personal Detection Strategy
**Rule**: Every Todoist project must contain a Google Drive link as a task
- **Work Project**: Contains link to work Google Drive account
- **Personal Project**: Contains link to personal Google Drive account  
- **Missing Link**: Flagged as requiring resolution

## Data Collection Requirements

### Todoist API
- Fetch all projects with favorite status
- Fetch all tasks for each project to find Google Drive links
- Parse Google Drive URLs to determine work vs personal account
- Extract folder IDs/names from Drive URLs

### Apple Notes AppleScript
- List all folders in "Projects" directory
- List all folders in "Areas" directory
- Handle nested structures if they exist

### Google Drive APIs (Both Accounts)
- List all folders in "2-@Area" directory
- Get starred status for each folder
- Match folder names with Todoist projects

## Setup Process

### Initial Setup (One-time)
1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get Todoist API token**
   - Go to Todoist Settings → Integrations → Developer
   - Copy API token to `config.yaml`

3. **Setup Google OAuth**
   - Visit Google Cloud Console
   - Create new project or use existing
   - Enable Google Drive API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download as `client_secrets.json`

4. **Configure accounts**
   - Edit `config.yaml` with your email domains
   - Adjust folder names if different

### First Run Authorization
```bash
python para_auditor.py --setup
```
- Opens browser twice (work account, then personal account)
- You'll see "Choose an account" - select work account first
- Grant permission to read Google Drive
- Repeat for personal account
- Tokens saved automatically for future runs

### Regular Usage
```bash
python para_auditor.py
```
- Runs full audit using saved credentials
- Generates report in specified format
- No browser interaction needed
