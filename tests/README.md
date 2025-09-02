# PARA Auditor Test Suite

This directory contains comprehensive tests for the PARA Auditor tool, with a focus on the new area handling functionality.

## Test Files

### `test_areas_handling.py`
Tests the core area handling functionality:

- **Area vs Project Logic**: Ensures areas only get next action checks, not cross-service sync validation
- **Report Generation**: Tests the `--show-all-areas` flag behavior
- **Duplicate Prevention**: Verifies no duplicate next action warnings for areas
- **Item Comparator**: Tests that different item types get appropriate checks
- **Mixed Group Handling**: Tests scenarios with both projects and areas

### `test_cli_areas.py`
Tests command line interface functionality:

- **Argument Parsing**: Verifies `--show-all-areas` flag is properly defined
- **Help Text**: Ensures appropriate help text is displayed
- **Filtering Logic**: Tests various filter combinations (work/personal, projects/areas)
- **Configuration Display**: Tests that area settings are shown in audit configuration
- **Integration**: End-to-end area handling workflow

### `conftest.py`
Provides common test fixtures and configuration:

- **Sample PARA Items**: Mock data for projects and areas with/without next actions
- **Mock Objects**: Config managers, comparison results, and metadata
- **Test Environment**: Sets up test directories and environment variables

## Test Coverage

The test suite covers:

1. **Core Area Logic**: Areas only get next action checks, projects get full sync validation
2. **Report Filtering**: `--show-all-areas` flag controls which areas are displayed
3. **Duplicate Prevention**: Filtering out `MISSING_NEXT_ACTION` inconsistencies for areas
4. **CLI Integration**: Command line argument handling and help text
5. **Filter Combinations**: Work/personal, projects/areas, and combined filters
6. **Configuration Display**: Showing area-related settings in audit output

## Running Tests

```bash
# Run all tests
uv run python -m pytest tests/ -v

# Run specific test file
uv run python -m pytest tests/test_areas_handling.py -v

# Run specific test class
uv run python -m pytest tests/test_areas_handling.py::TestAreaHandling -v

# Run with coverage
uv run python -m pytest tests/ --cov=src --cov-report=html
```

## Test Results

All 21 tests pass, providing confidence that:

- Areas are handled correctly (next actions only, no sync checks)
- Projects get full cross-service validation
- The `--show-all-areas` flag works as expected
- No duplicate warnings are generated
- CLI arguments are properly parsed and displayed
- Filter combinations work logically
- Configuration display shows area settings

## Key Test Scenarios

### Area Handling
- Areas without next actions show instruction to create one
- Areas with next actions are filtered out by default
- `--show-all-areas` shows all areas regardless of next action status

### Project Handling
- Projects get full cross-service sync validation
- Missing folders in Google Drive and Apple Notes are detected
- Inconsistencies across services are reported

### Duplicate Prevention
- `MISSING_NEXT_ACTION` inconsistencies for areas are filtered out
- Only the instruction to create next actions is shown
- No duplicate actionable items in reports

### CLI Integration
- `--show-all-areas` works with all other flags
- Help text is clear and informative
- Configuration display shows current area settings
