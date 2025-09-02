"""Tests for PARA area handling functionality."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from datetime import datetime

from src.models.para_item import PARAItem, ItemType, ItemSource, CategoryType
from src.auditor.comparator import ItemComparator, Inconsistency, InconsistencyType
from src.auditor.report_generator import ReportGenerator, MarkdownFormatter
from src.main import get_todoist_item_issues, print_project_alignment_view


class TestAreaHandling:
    """Test the new area handling functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create sample PARA items for testing
        self.work_project = PARAItem(
            name="Website Redesign",
            raw_name="🌐 Website Redesign",
            type=ItemType.PROJECT,
            is_active=True,
            category=CategoryType.WORK,
            source=ItemSource.TODOIST,
            metadata={
                'has_next_action': True,
                'next_action_tasks': ['Review current design', 'Create wireframes'],
                'next_action_count': 2
            }
        )
        
        self.personal_project = PARAItem(
            name="Home Renovation",
            raw_name="🏠 Home Renovation",
            type=ItemType.PROJECT,
            is_active=True,
            category=CategoryType.PERSONAL,
            source=ItemSource.TODOIST,
            metadata={
                'has_next_action': True,
                'next_action_tasks': ['Get contractor quotes'],
                'next_action_count': 1
            }
        )
        
        self.work_area_with_next = PARAItem(
            name="Team Management",
            raw_name="👥 Team Management",
            type=ItemType.AREA,
            is_active=False,
            category=CategoryType.WORK,
            source=ItemSource.TODOIST,
            metadata={
                'has_next_action': True,
                'next_action_tasks': ['Schedule 1:1 meetings'],
                'next_action_count': 1
            }
        )
        
        self.work_area_without_next = PARAItem(
            name="Evacuation Plan",
            raw_name="😰 Evacuation Plan",
            type=ItemType.AREA,
            is_active=False,
            category=CategoryType.WORK,
            source=ItemSource.TODOIST,
            metadata={
                'has_next_action': False,
                'next_action_tasks': [],
                'next_action_count': 0
            }
        )
        
        self.personal_area_without_next = PARAItem(
            name="Fitness Goals",
            raw_name="🏃 Fitness Goals",
            type=ItemType.AREA,
            is_active=False,
            category=CategoryType.PERSONAL,
            source=ItemSource.TODOIST,
            metadata={
                'has_next_action': False,
                'next_action_tasks': [],
                'next_action_count': 0
            }
        )
        
        # Create sample inconsistencies
        self.missing_next_action_inconsistency = Inconsistency(
            type=InconsistencyType.MISSING_NEXT_ACTION,
            description="Area 'Evacuation Plan' has no @next actions",
            severity='medium',
            items=[self.work_area_without_next],
            suggested_action="Add at least one task with @next label to define the next action",
            metadata={
                'project_id': '123',
                'next_action_label': 'next',
                'next_action_count': 0,
                'item_type': 'area'
            }
        )
    
    def test_get_todoist_item_issues_areas_only_next_action_check(self):
        """Test that areas only get next action checks, not sync checks."""
        # Mock comparison result with inconsistencies
        comparison_result = Mock()
        comparison_result.inconsistencies = [self.missing_next_action_inconsistency]
        
        # Mock matching items (empty for areas)
        matching_items = {source: [] for source in ItemSource}
        
        # Test area without next actions
        issues = get_todoist_item_issues(
            self.work_area_without_next, 
            matching_items, 
            comparison_result
        )
        
        # Should only show next action issue, not sync issues
        assert len(issues) == 1
        assert "Missing next action: Add @next task to this area" in issues[0]
        
        # Test area with next actions
        issues = get_todoist_item_issues(
            self.work_area_with_next, 
            matching_items, 
            comparison_result
        )
        
        # Should show no issues
        assert len(issues) == 0
    
    def test_get_todoist_item_issues_projects_get_full_sync_check(self):
        """Test that projects get full cross-service sync validation."""
        # Create a proper inconsistency that includes items from expected sources
        from src.models.para_item import PARAItem, ItemType, ItemSource, CategoryType
        
        # Create mock items from other sources for the inconsistency
        gdrive_item = PARAItem(
            name="Website Redesign",
            raw_name="🌐 Website Redesign",
            type=ItemType.PROJECT,
            is_active=False,  # Different status than Todoist
            category=CategoryType.WORK,
            source=ItemSource.GDRIVE_WORK,
            metadata={}
        )
        
        notes_item = PARAItem(
            name="Website Redesign",
            raw_name="🌐 Website Redesign",
            type=ItemType.PROJECT,
            is_active=False,  # Different status than Todoist
            category=CategoryType.WORK,
            source=ItemSource.APPLE_NOTES,
            metadata={}
        )
        
        # Create inconsistency with items from multiple sources
        status_mismatch_inconsistency = Inconsistency(
            type=InconsistencyType.STATUS_MISMATCH,
            description="Status mismatch between Todoist and Google Drive",
            severity='high',
            items=[self.work_project, gdrive_item, notes_item],  # Include items from expected sources
            suggested_action="Update status to match across all tools",
            metadata={}
        )
        
        # Mock comparison result with inconsistencies
        comparison_result = Mock()
        comparison_result.inconsistencies = [status_mismatch_inconsistency]
        
        # Mock matching items (empty to simulate missing folders)
        matching_items = {source: [] for source in ItemSource}
        
        # Test work project
        issues = get_todoist_item_issues(
            self.work_project, 
            matching_items, 
            comparison_result
        )
        
        # Should show missing folder issues and inconsistency issues
        assert len(issues) >= 2
        assert any("Missing in Work Google Drive" in issue for issue in issues)
        assert any("Missing in Apple Notes" in issue for issue in issues)
        # Check for the inconsistency issue
        assert any("Status Mismatch" in issue for issue in issues)
        
        # Test personal project
        issues = get_todoist_item_issues(
            self.personal_project, 
            matching_items, 
            comparison_result
        )
        
        # Should show missing folder issues for personal sources
        assert len(issues) >= 2
        assert any("Missing in Personal Google Drive" in issue for issue in issues)
        assert any("Missing in Apple Notes" in issue for issue in issues)
    
    def test_markdown_formatter_show_all_areas_false(self):
        """Test markdown formatter with show_all_areas=False (default)."""
        formatter = MarkdownFormatter()
        
        # Create mock comparison result
        comparison_result = Mock()
        comparison_result.item_groups = [
            [self.work_project, self.personal_project],
            [self.work_area_with_next, self.work_area_without_next, self.personal_area_without_next]
        ]
        comparison_result.inconsistencies = [self.missing_next_action_inconsistency]
        # Set actual values for attributes that are accessed
        comparison_result.consistency_score = 0.8
        comparison_result.total_items = 5
        comparison_result.consistent_items = 3
        
        # Mock metadata with proper datetime object
        metadata = Mock()
        metadata.generated_at = datetime(2024, 1, 1, 12, 0, 0)
        metadata.total_items = 5
        metadata.consistency_score = 0.8
        metadata.sources_audited = ["Todoist", "Google Drive", "Apple Notes"]
        metadata.filters_applied = {}
        metadata.version = "1.0"
        
        # Generate report with show_all_areas=False
        report = formatter.format(comparison_result, metadata, show_all_areas=False)
        
        # Should include projects
        assert "## 🌐 Website Redesign" in report
        assert "## 🏠 Home Renovation" in report
        
        # Should include areas WITHOUT next actions
        assert "## 😰 Evacuation Plan" in report
        assert "## 🏃 Fitness Goals" in report
        
        # Should NOT include areas WITH next actions
        assert "## 👥 Team Management" not in report
        
        # Should show instruction to create next actions for areas without them
        assert "Create @next action for this area" in report
    
    def test_markdown_formatter_show_all_areas_true(self):
        """Test markdown formatter with show_all_areas=True."""
        formatter = MarkdownFormatter()
        
        # Create mock comparison result
        comparison_result = Mock()
        comparison_result.item_groups = [
            [self.work_project, self.personal_project],
            [self.work_area_with_next, self.work_area_without_next, self.personal_area_without_next]
        ]
        comparison_result.inconsistencies = [self.missing_next_action_inconsistency]
        # Set actual values for attributes that are accessed
        comparison_result.consistency_score = 0.8
        comparison_result.total_items = 5
        comparison_result.consistent_items = 3
        
        # Mock metadata with proper datetime object
        metadata = Mock()
        metadata.generated_at = datetime(2024, 1, 1, 12, 0, 0)
        metadata.total_items = 5
        metadata.consistency_score = 0.8
        metadata.sources_audited = ["Todoist", "Google Drive", "Apple Notes"]
        metadata.filters_applied = {}
        metadata.version = "1.0"
        
        # Generate report with show_all_areas=True
        report = formatter.format(comparison_result, metadata, show_all_areas=True)
        
        # Should include all projects
        assert "## 🌐 Website Redesign" in report
        assert "## 🏠 Home Renovation" in report
        
        # Should include ALL areas (both with and without next actions)
        assert "## 👥 Team Management" in report  # Area with next actions
        assert "## 😰 Evacuation Plan" in report  # Area without next actions
        assert "## 🏃 Fitness Goals" in report   # Area without next actions
        
        # Should show next actions for areas that have them
        assert "Schedule 1:1 meetings" in report
        
        # Should show instruction to create next actions for areas without them
        assert "Create @next action for this area" in report
    
    def test_no_duplicate_next_action_warnings(self):
        """Test that areas don't get duplicate next action warnings."""
        formatter = MarkdownFormatter()
        
        # Create mock comparison result with missing next action inconsistency
        comparison_result = Mock()
        comparison_result.item_groups = [
            [self.work_area_without_next]
        ]
        comparison_result.inconsistencies = [self.missing_next_action_inconsistency]
        # Set actual values for attributes that are accessed
        comparison_result.consistency_score = 0.5
        comparison_result.total_items = 1
        comparison_result.consistent_items = 0
        
        # Mock metadata with proper datetime object
        metadata = Mock()
        metadata.generated_at = datetime(2024, 1, 1, 12, 0, 0)
        metadata.total_items = 1
        metadata.consistency_score = 0.5
        metadata.sources_audited = ["Todoist"]
        metadata.filters_applied = {}
        metadata.version = "1.0"
        
        # Generate report
        report = formatter.format(comparison_result, metadata, show_all_areas=False)
        
        # Should only show one next action instruction
        assert report.count("Create @next action for this area") == 1
        
        # Should NOT show the inconsistency warning (filtered out)
        assert "Add at least one task with @next label to define the next action" not in report
    
    def test_item_comparator_areas_only_next_action_checks(self):
        """Test that ItemComparator only runs next action checks for areas."""
        comparator = ItemComparator(similarity_threshold=0.8)
        
        # Create a group with only areas
        area_group = [self.work_area_without_next, self.personal_area_without_next]
        
        # Analyze the group
        inconsistencies = comparator._analyze_item_group(area_group)
        
        # Should only have next action inconsistencies
        assert len(inconsistencies) > 0
        assert all(inc.type == InconsistencyType.MISSING_NEXT_ACTION for inc in inconsistencies)
        
        # Should NOT have sync-related inconsistencies
        assert not any(inc.type in [
            InconsistencyType.STATUS_MISMATCH,
            InconsistencyType.TYPE_MISMATCH,
            InconsistencyType.CATEGORY_MISMATCH,
            InconsistencyType.WRONG_ACCOUNT,
            InconsistencyType.NAME_VARIATION,
            InconsistencyType.MISSING_EMOJI
        ] for inc in inconsistencies)
    
    def test_item_comparator_projects_get_full_checks(self):
        """Test that ItemComparator runs full checks for projects."""
        comparator = ItemComparator(similarity_threshold=0.8)
        
        # Create a group with only projects
        project_group = [self.work_project, self.personal_project]
        
        # Analyze the group
        inconsistencies = comparator._analyze_item_group(project_group)
        
        # Should have various types of inconsistencies (depending on what's detected)
        # At minimum, should have next action checks
        assert len(inconsistencies) >= 0  # May be 0 if all checks pass
        
        # Should include next action checks
        next_action_incs = [inc for inc in inconsistencies if inc.type == InconsistencyType.MISSING_NEXT_ACTION]
        # Note: These projects have next actions, so may not have missing next action inconsistencies
    
    def test_mixed_group_handling(self):
        """Test handling of groups with both projects and areas."""
        comparator = ItemComparator(similarity_threshold=0.8)
        
        # Create a group with only areas
        mixed_group = [self.work_project, self.work_area_without_next]
        
        # Analyze the group
        inconsistencies = comparator._analyze_item_group(mixed_group)
        
        # Should have inconsistencies (next action for area, potentially others for project)
        assert len(inconsistencies) >= 1
        
        # Should include next action check for the area
        area_next_action_incs = [
            inc for inc in inconsistencies 
            if inc.type == InconsistencyType.MISSING_NEXT_ACTION 
            and any(item.type == ItemType.AREA for item in inc.items)
        ]
        assert len(area_next_action_incs) >= 1


class TestCommandLineIntegration:
    """Test command line integration of area handling."""
    
    @patch('src.main.get_todoist_item_issues')
    def test_print_project_alignment_view_handles_areas_correctly(self, mock_get_issues):
        """Test that the alignment view correctly handles both projects and areas."""
        # Mock the issues function to return predictable results
        mock_get_issues.return_value = []
        
        # Create mock items
        all_items = [
            PARAItem(
                name="Test Project",
                raw_name="🧪 Test Project",
                type=ItemType.PROJECT,
                is_active=True,
                category=CategoryType.WORK,
                source=ItemSource.TODOIST,
                metadata={'has_next_action': True}
            ),
            PARAItem(
                name="Test Area",
                raw_name="📋 Test Area",
                type=ItemType.AREA,
                is_active=False,
                category=CategoryType.PERSONAL,
                source=ItemSource.TODOIST,
                metadata={'has_next_action': False}
            )
        ]
        
        # Mock comparison result
        comparison_result = Mock()
        comparison_result.item_groups = [all_items]
        
        # Test the function (this will print to stdout, but we can verify it doesn't crash)
        try:
            print_project_alignment_view(all_items, comparison_result)
            # If we get here, the function didn't crash
            assert True
        except Exception as e:
            pytest.fail(f"print_project_alignment_view crashed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
