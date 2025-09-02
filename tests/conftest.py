"""Pytest configuration and common fixtures for PARA Auditor tests."""

import pytest
from unittest.mock import Mock
from pathlib import Path

from src.models.para_item import PARAItem, ItemType, ItemSource, CategoryType


@pytest.fixture
def sample_para_items():
    """Provide sample PARA items for testing."""
    return {
        'work_project': PARAItem(
            name="Website Redesign",
            raw_name="🌐 Website Redesign",
            type=ItemType.PROJECT,
            is_active=True,
            category=CategoryType.WORK,
            source=ItemSource.TODOIST,
            metadata={
                'has_next_action': True,
                'next_action_tasks': ['Review current design', 'Create wireframes'],
                'next_action_count': 2,
                'project_id': 'proj_1'
            }
        ),
        'personal_project': PARAItem(
            name="Home Renovation",
            raw_name="🏠 Home Renovation",
            type=ItemType.PROJECT,
            is_active=True,
            category=CategoryType.PERSONAL,
            source=ItemSource.TODOIST,
            metadata={
                'has_next_action': True,
                'next_action_tasks': ['Get contractor quotes'],
                'next_action_count': 1,
                'project_id': 'proj_2'
            }
        ),
        'work_area_with_next': PARAItem(
            name="Team Management",
            raw_name="👥 Team Management",
            type=ItemType.AREA,
            is_active=False,
            category=CategoryType.WORK,
            source=ItemSource.TODOIST,
            metadata={
                'has_next_action': True,
                'next_action_tasks': ['Schedule 1:1 meetings'],
                'next_action_count': 1,
                'project_id': 'area_1'
            }
        ),
        'work_area_without_next': PARAItem(
            name="Evacuation Plan",
            raw_name="😰 Evacuation Plan",
            type=ItemType.AREA,
            is_active=False,
            category=CategoryType.WORK,
            source=ItemSource.TODOIST,
            metadata={
                'has_next_action': False,
                'next_action_tasks': [],
                'next_action_count': 0,
                'project_id': 'area_2'
            }
        ),
        'personal_area_with_next': PARAItem(
            name="Fitness Goals",
            raw_name="🏃 Fitness Goals",
            type=ItemType.AREA,
            is_active=False,
            category=CategoryType.PERSONAL,
            source=ItemSource.TODOIST,
            metadata={
                'has_next_action': True,
                'next_action_tasks': ['Go to gym 3x/week'],
                'next_action_count': 1,
                'project_id': 'area_3'
            }
        ),
        'personal_area_without_next': PARAItem(
            name="Reading List",
            raw_name="📚 Reading List",
            type=ItemType.AREA,
            is_active=False,
            category=CategoryType.PERSONAL,
            source=ItemSource.TODOIST,
            metadata={
                'has_next_action': False,
                'next_action_tasks': [],
                'next_action_count': 0,
                'project_id': 'area_4'
            }
        )
    }


@pytest.fixture
def mock_config_manager():
    """Provide a mock configuration manager for testing."""
    config = Mock()
    config.work_domain = "@company.com"
    config.personal_domain = "@gmail.com"
    config.projects_folder = "Projects"
    config.areas_folder = "Areas"
    config.next_action_label = "next"
    config.work_client_secrets_path = "config/credentials/work_client_secrets.json"
    config.personal_client_secrets_path = "config/credentials/personal_client_secrets.json"
    config.credentials_dir = Path("config/credentials")
    config.todoist_token = "test_token_123"
    config.gdrive_base_folder_name = "2-@Areas"
    return config


@pytest.fixture
def mock_comparison_result():
    """Provide a mock comparison result for testing."""
    result = Mock()
    result.total_items = 6
    result.consistent_items = 4
    result.consistency_score = 0.67
    result.inconsistencies = []
    result.item_groups = []
    result.high_severity_count = 0
    result.medium_severity_count = 0
    result.low_severity_count = 0
    return result


@pytest.fixture
def mock_report_metadata():
    """Provide mock report metadata for testing."""
    metadata = Mock()
    metadata.generated_at = "2024-01-01 12:00:00"
    metadata.total_items = 6
    metadata.consistency_score = 0.67
    metadata.sources_audited = ["Todoist", "Google Drive", "Apple Notes"]
    metadata.filters_applied = {}
    metadata.version = "1.0"
    return metadata


@pytest.fixture
def sample_inconsistencies():
    """Provide sample inconsistencies for testing."""
    return [
        {
            'type': 'missing_next_action',
            'description': "Area 'Evacuation Plan' has no @next actions",
            'severity': 'medium',
            'items': ['work_area_without_next'],
            'suggested_action': "Add at least one task with @next label to define the next action"
        },
        {
            'type': 'status_mismatch',
            'description': "Status mismatch between Todoist and Google Drive",
            'severity': 'high',
            'items': ['work_project'],
            'suggested_action': "Update status to match across all tools"
        },
        {
            'type': 'missing_item',
            'description': "Project not found in Google Drive",
            'severity': 'high',
            'items': ['personal_project'],
            'suggested_action': "Create corresponding folder in Google Drive"
        }
    ]


@pytest.fixture
def mock_args():
    """Provide mock command line arguments for testing."""
    args = Mock()
    args.verbose = False
    args.quiet = False
    args.dry_run = False
    args.threshold = 0.8
    args.format = 'markdown'
    args.output = None
    args.work_only = False
    args.personal_only = False
    args.projects_only = False
    args.areas_only = False
    args.show_all_areas = False
    args.next_action_label = None
    args.skip_next_actions = False
    return args


@pytest.fixture
def temp_test_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, tmp_path):
    """Set up test environment variables and paths."""
    # Set test environment variables
    monkeypatch.setenv('PARA_AUDITOR_CONFIG', str(tmp_path / 'test_config.yaml'))
    monkeypatch.setenv('PARA_AUDITOR_CREDENTIALS', str(tmp_path / 'credentials'))
    
    # Create test directories
    (tmp_path / 'credentials').mkdir(exist_ok=True)
    
    yield
    
    # Cleanup (if needed)
    pass
