# PARA Auditor - Implementation Plan

## Project Structure

```
para_auditor/
├── config/
│   ├── client_secrets.json          # Google OAuth credentials (user provides)
│   ├── config.yaml                  # Main configuration (user edits)
│   └── credentials/                 # Auto-generated token storage
│       ├── work_drive_token.pickle
│       └── personal_drive_token.pickle
├── src/
│   ├── __init__.py
│   ├── main.py                      # Entry point and CLI
│   ├── config_manager.py            # Configuration loading and validation
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── google_auth.py           # Google OAuth flow
│   │   └── todoist_auth.py          # Todoist API token handling
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── todoist_connector.py     # Todoist API integration
│   │   ├── gdrive_connector.py      # Google Drive API integration
│   │   └── apple_notes_connector.py # AppleScript integration
│   ├── models/
│   │   ├── __init__.py
│   │   └── para_item.py             # PARAItem dataclass and utilities
│   ├── auditor/
│   │   ├── __init__.py
│   │   ├── comparator.py            # Logic for comparing items across tools
│   │   ├── emoji_suggester.py       # Emoji suggestion logic
│   │   └── report_generator.py      # Output formatting
│   └── utils/
│       ├── __init__.py
│       ├── name_matcher.py          # Fuzzy name matching utilities
│       └── url_parser.py            # Google Drive URL parsing
├── scripts/
│   └── applescript/
│       └── get_notes_folders.scpt   # AppleScript for Notes integration
├── tests/
│   ├── __init__.py
│   ├── test_connectors.py
│   ├── test_auditor.py
│   └── fixtures/
│       └── sample_data.json
├── requirements.txt
├── setup.py
├── README.md
└── .gitignore
```

## Implementation Phases

### Phase 1: Foundation (2-3 hours)
**Goal**: Basic project structure and configuration system

1. **Project Setup**
   - Create directory structure
   - Set up `requirements.txt` and `setup.py`
   - Create `.gitignore` (exclude credentials, tokens)

2. **Configuration Management** (`config_manager.py`)
   - YAML config loading with validation
   - Environment variable support for sensitive data
   - Default configuration generation
   - Config validation and error reporting

3. **Data Models** (`models/para_item.py`)
   - `PARAItem` dataclass with validation
   - Utility methods for comparison and normalization
   - Enum classes for item types and sources

4. **CLI Framework** (`main.py`)
   - Argument parsing (setup vs audit modes)
   - Basic error handling and logging
   - Configuration path handling

### Phase 2: Authentication (2-3 hours)
**Goal**: All authentication flows working

1. **Google OAuth** (`auth/google_auth.py`)
   - OAuth flow for desktop applications
   - Token storage and refresh logic
   - Support for multiple accounts (work/personal)
   - Domain-based account identification

2. **Todoist Auth** (`auth/todoist_auth.py`)
   - API token validation
   - Connection testing
   - Rate limiting awareness

3. **Setup Command**
   - `--setup` mode for initial OAuth flows
   - Interactive account selection
   - Credential validation and storage

### Phase 3: Data Collection (4-5 hours)
**Goal**: Gather data from all sources

1. **Todoist Connector** (`connectors/todoist_connector.py`)
   - Fetch all projects with metadata
   - Extract favorite status
   - Fetch tasks for each project
   - Parse Google Drive links from task content
   - URL parsing and account identification

2. **Google Drive Connector** (`connectors/gdrive_connector.py`)
   - List folders in "2-@Area" directory
   - Get folder metadata (starred status, name, ID)
   - Support both work and personal accounts
   - Handle pagination and rate limits

3. **Apple Notes Connector** (`connectors/apple_notes_connector.py`)
   - AppleScript execution framework
   - Extract folder lists from Projects and Areas
   - Error handling for AppleScript failures
   - Support for nested folder structures

4. **URL Parser** (`utils/url_parser.py`)
   - Parse Google Drive URLs from various formats
   - Extract folder IDs and names
   - Determine account type from domain
   - Handle malformed URLs gracefully

### Phase 4: Comparison Logic (3-4 hours)
**Goal**: Identify inconsistencies across tools

1. **Name Matching** (`utils/name_matcher.py`)
   - Fuzzy string matching for similar names
   - Normalization rules (remove special chars, etc.)
   - Configurable similarity thresholds
   - Handle emoji prefixes in matching

2. **Item Comparator** (`auditor/comparator.py`)
   - Cross-tool item matching
   - Status consistency checking
   - Missing item detection
   - Account placement validation
   - Link-folder relationship validation

3. **Emoji Detection** (`auditor/emoji_suggester.py`)
   - Unicode emoji detection at string start
   - Keyword-based emoji suggestions
   - Category-based suggestions (work vs personal)
   - Multiple suggestion support

### Phase 5: Reporting (2-3 hours)
**Goal**: Generate comprehensive audit reports

1. **Report Generator** (`auditor/report_generator.py`)
   - Multiple output formats (Markdown, JSON, plain text)
   - Prioritized issue categorization
   - Clear action recommendations
   - Summary statistics
   - Configurable verbosity levels

2. **Report Templates**
   - Structured report sections
   - Color coding for different issue types
   - Progress tracking for large audits

### Phase 6: Testing & Polish (2-3 hours)
**Goal**: Robust, production-ready tool

1. **Unit Tests**
   - Test configuration loading
   - Mock API responses for connector testing
   - Test comparison logic with known data
   - Test report generation

2. **Integration Testing**
   - End-to-end audit with sample data
   - OAuth flow testing
   - Error handling verification

3. **Documentation**
   - Setup instructions
   - Troubleshooting guide
   - Configuration reference
   - Usage examples

## Key Implementation Details

### Google OAuth Flow
```python
# Separate flows for work and personal accounts
def authenticate_account(account_type: str, domain: str):
    flow = InstalledAppFlow.from_client_secrets_file(
        'config/client_secrets.json', 
        SCOPES
    )
    # Custom authorization URL with domain hint
    creds = flow.run_local_server(
        port=0,
        prompt='select_account',
        authorization_prompt_message=f'Please sign in to your {account_type} account ({domain})'
    )
    # Save tokens with account-specific names
    save_token(creds, f'{account_type}_drive_token.pickle')
```

### Todoist Google Drive Link Parsing
```python
def extract_gdrive_links(project_tasks: List[Task]) -> List[str]:
    gdrive_patterns = [
        r'https://drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)',
        r'https://drive\.google\.com/drive/u/\d+/folders/([a-zA-Z0-9_-]+)',
        # Handle various Google Drive URL formats
    ]
    # Extract all matching URLs from task content
    # Determine account type from domain in URL
```

### AppleScript Integration
```applescript
-- scripts/applescript/get_notes_folders.scpt
tell application "Notes"
    set projectFolders to {}
    set areaFolders to {}
    
    repeat with theFolder in folders of folder "Projects"
        set end of projectFolders to name of theFolder
    end repeat
    
    repeat with theFolder in folders of folder "Areas"
        set end of areaFolders to name of theFolder
    end repeat
    
    return {projects:projectFolders, areas:areaFolders}
end tell
```

### Error Handling Strategy
- Graceful degradation when services are unavailable
- Clear error messages for authentication issues
- Retry logic for rate-limited API calls
- Validation of all external data before processing
- Comprehensive logging for debugging

### Performance Considerations
- Batch API requests where possible
- Cache Google Drive folder listings
- Parallel processing for independent API calls
- Progress indicators for long-running operations

## Development Timeline

**Total Estimated Time**: 15-20 hours spread over 1-2 weeks

- **Week 1**: Phases 1-3 (Foundation, Auth, Data Collection)
- **Week 2**: Phases 4-6 (Comparison, Reporting, Testing)

## Testing Strategy

### Unit Testing
- Mock all external API calls
- Test configuration edge cases
- Validate comparison logic with known data sets
- Test emoji detection and suggestion accuracy

### Integration Testing
- Real API testing with test accounts
- End-to-end audit workflow
- Error recovery scenarios
- Performance testing with large data sets

### Manual Testing
- OAuth flow on fresh machine
- Various Google Drive folder structures
- Different Apple Notes configurations
- Report output validation

## Deployment & Distribution

### Installation Methods
1. **Direct Git Clone**: For development and customization
2. **pip install**: Package for PyPI distribution
3. **Standalone Binary**: PyInstaller for non-Python users

### Configuration Management
- Template config file generation
- Environment variable overrides for sensitive data
- Validation of required configuration sections
- Migration support for config format changes