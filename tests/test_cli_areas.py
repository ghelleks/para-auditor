"""Tests for command line argument handling of area-related functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import argparse

from src.main import create_parser, apply_filters, print_audit_configuration
from src.models.para_item import PARAItem, ItemType, ItemSource, CategoryType


class TestCommandLineArguments:
    """Test command line argument parsing for area handling."""
    
    def test_show_all_areas_argument_exists(self):
        """Test that --show-all-areas argument is properly defined."""
        parser = create_parser()
        
        # Check that the argument exists
        assert hasattr(parser, 'parse_args')
        
        # Parse with the flag
        args = parser.parse_args(['--show-all-areas'])
        assert args.show_all_areas is True
        
        # Parse without the flag (should default to False)
        args = parser.parse_args([])
        assert args.show_all_areas is False
    
    def test_show_all_areas_help_text(self):
        """Test that --show-all-areas has appropriate help text."""
        parser = create_parser()
        
        # Get help text
        help_text = parser.format_help()
        
        # Should contain the flag description
        assert '--show-all-areas' in help_text
        assert 'Show all PARA areas in the report' in help_text
        # The help text format shows the description on multiple lines
        assert 'default: only show' in help_text
        assert 'areas missing next actions' in help_text
    
    def test_show_all_areas_with_other_flags(self):
        """Test that --show-all-areas works with other relevant flags."""
        parser = create_parser()
        
        # Test with areas-only flag
        args = parser.parse_args(['--areas-only', '--show-all-areas'])
        assert args.areas_only is True
        assert args.show_all_areas is True
        
        # Test with projects-only flag
        args = parser.parse_args(['--projects-only', '--show-all-areas'])
        assert args.projects_only is True
        assert args.show_all_areas is True
        
        # Test with work-only flag
        args = parser.parse_args(['--work-only', '--show-all-areas'])
        assert args.work_only is True
        assert args.show_all_areas is True
        
        # Test with personal-only flag
        args = parser.parse_args(['--personal-only', '--show-all-areas'])
        assert args.personal_only is True
        assert args.show_all_areas is True
    
    def test_show_all_areas_mutual_exclusivity(self):
        """Test that --show-all-areas doesn't conflict with other flags."""
        parser = create_parser()
        
        # These should all work together
        args = parser.parse_args([
            '--show-all-areas',
            '--verbose',
            '--threshold', '0.9',
            '--format', 'json'
        ])
        
        assert args.show_all_areas is True
        assert args.verbose is True
        assert args.threshold == 0.9
        assert args.format == 'json'


class TestFilteringLogic:
    """Test the filtering logic for areas."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.work_project = PARAItem(
            name="Work Project",
            raw_name="💼 Work Project",
            type=ItemType.PROJECT,
            is_active=True,
            category=CategoryType.WORK,
            source=ItemSource.TODOIST,
            metadata={'has_next_action': True}
        )
        
        self.personal_project = PARAItem(
            name="Personal Project",
            raw_name="🏠 Personal Project",
            type=ItemType.PROJECT,
            is_active=True,
            category=CategoryType.PERSONAL,
            source=ItemSource.TODOIST,
            metadata={'has_next_action': True}
        )
        
        self.work_area_with_next = PARAItem(
            name="Work Area",
            raw_name="📋 Work Area",
            type=ItemType.AREA,
            is_active=False,
            category=CategoryType.WORK,
            source=ItemSource.TODOIST,
            metadata={'has_next_action': True}
        )
        
        self.work_area_without_next = PARAItem(
            name="Work Area No Next",
            raw_name="📋 Work Area No Next",
            type=ItemType.AREA,
            is_active=False,
            category=CategoryType.WORK,
            source=ItemSource.TODOIST,
            metadata={'has_next_action': False}
        )
        
        self.personal_area_with_next = PARAItem(
            name="Personal Area",
            raw_name="📋 Personal Area",
            type=ItemType.AREA,
            is_active=False,
            category=CategoryType.PERSONAL,
            source=ItemSource.TODOIST,
            metadata={'has_next_action': True}
        )
        
        self.personal_area_without_next = PARAItem(
            name="Personal Area No Next",
            raw_name="📋 Personal Area No Next",
            type=ItemType.AREA,
            is_active=False,
            category=CategoryType.PERSONAL,
            source=ItemSource.TODOIST,
            metadata={'has_next_action': False}
        )
        
        self.all_items = [
            self.work_project,
            self.personal_project,
            self.work_area_with_next,
            self.work_area_without_next,
            self.personal_area_with_next,
            self.personal_area_without_next
        ]
    
    def test_areas_only_filter(self):
        """Test that --areas-only filter works correctly."""
        args = Mock()
        args.areas_only = True
        args.work_only = False
        args.personal_only = False
        args.projects_only = False
        
        filtered = apply_filters(self.all_items, args)
        
        # Should only include areas
        assert len(filtered) == 4
        assert all(item.type == ItemType.AREA for item in filtered)
        assert self.work_project not in filtered
        assert self.personal_project not in filtered
    
    def test_projects_only_filter(self):
        """Test that --projects-only filter works correctly."""
        args = Mock()
        args.areas_only = False
        args.work_only = False
        args.personal_only = False
        args.projects_only = True
        
        filtered = apply_filters(self.all_items, args)
        
        # Should only include projects
        assert len(filtered) == 2
        assert all(item.type == ItemType.PROJECT for item in filtered)
        assert self.work_area_with_next not in filtered
        assert self.personal_area_without_next not in filtered
    
    def test_work_only_filter(self):
        """Test that --work-only filter works correctly."""
        args = Mock()
        args.areas_only = False
        args.work_only = True
        args.personal_only = False
        args.projects_only = False
        
        filtered = apply_filters(self.all_items, args)
        
        # Should only include work items
        assert len(filtered) == 3
        assert all(item.category == CategoryType.WORK for item in filtered)
        assert self.personal_project not in filtered
        assert self.personal_area_with_next not in filtered
    
    def test_personal_only_filter(self):
        """Test that --personal-only filter works correctly."""
        args = Mock()
        args.areas_only = False
        args.work_only = False
        args.personal_only = True
        args.projects_only = False
        
        filtered = apply_filters(self.all_items, args)
        
        # Should only include personal items
        assert len(filtered) == 3
        assert all(item.category == CategoryType.PERSONAL for item in filtered)
        assert self.work_project not in filtered
        assert self.work_area_with_next not in filtered
    
    def test_combined_filters(self):
        """Test that filters can be combined logically."""
        args = Mock()
        args.areas_only = True
        args.work_only = True
        args.personal_only = False
        args.projects_only = False
        
        filtered = apply_filters(self.all_items, args)
        
        # Should only include work areas
        assert len(filtered) == 2
        assert all(item.type == ItemType.AREA and item.category == CategoryType.WORK for item in filtered)
        assert self.work_area_with_next in filtered
        assert self.work_area_without_next in filtered


class TestConfigurationDisplay:
    """Test the configuration display for area handling."""
    
    def test_show_all_areas_configuration_display(self):
        """Test that show_all_areas setting is displayed in configuration."""
        # Mock config manager
        config_manager = Mock()
        config_manager.work_domain = "@company.com"
        config_manager.personal_domain = "@gmail.com"
        config_manager.projects_folder = "Projects"
        config_manager.areas_folder = "Areas"
        config_manager.next_action_label = "next"
        
        # Test with show_all_areas=True
        args = Mock()
        args.threshold = 0.8
        args.work_only = False
        args.personal_only = False
        args.projects_only = False
        args.areas_only = False
        args.show_all_areas = True
        args.next_action_label = None
        args.skip_next_actions = False
        
        # Capture stdout to check output
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            print_audit_configuration(config_manager, args)
        
        output = f.getvalue()
        
        # Should show the show_all_areas setting
        assert "Show All Areas: Yes" in output
    
    def test_show_all_areas_configuration_display_default(self):
        """Test that show_all_areas default is displayed in configuration."""
        # Mock config manager
        config_manager = Mock()
        config_manager.work_domain = "@company.com"
        config_manager.personal_domain = "@gmail.com"
        config_manager.projects_folder = "Projects"
        config_manager.areas_folder = "Areas"
        config_manager.next_action_label = "next"
        
        # Test with show_all_areas=False (default)
        args = Mock()
        args.threshold = 0.8
        args.work_only = False
        args.personal_only = False
        args.projects_only = False
        args.areas_only = False
        args.show_all_areas = False
        args.next_action_label = None
        args.skip_next_actions = False
        
        # Capture stdout to check output
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            print_audit_configuration(config_manager, args)
        
        output = f.getvalue()
        
        # Should show the default setting
        assert "Show All Areas: No (default)" in output


class TestIntegration:
    """Integration tests for area handling."""
    
    @patch('src.main.get_todoist_item_issues')
    def test_end_to_end_area_handling(self, mock_get_issues):
        """Test end-to-end area handling workflow."""
        # Mock the issues function
        mock_get_issues.return_value = []
        
        # Create a simple test scenario
        from src.main import print_project_alignment_view
        
        all_items = [
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
        
        comparison_result = Mock()
        comparison_result.item_groups = [all_items]
        
        # This should not crash and should handle areas correctly
        try:
            print_project_alignment_view(all_items, comparison_result)
            assert True  # If we get here, it worked
        except Exception as e:
            pytest.fail(f"End-to-end test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
