"""Report generation system with multiple output formats for PARA audit results."""
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from .comparator import ComparisonResult, Inconsistency, InconsistencyType
from ..models.para_item import PARAItem, ItemSource, ItemType, CategoryType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ReportMetadata:
    """Metadata for audit reports."""
    generated_at: datetime
    total_items: int
    consistency_score: float
    sources_audited: List[str]
    filters_applied: Dict[str, Any]
    version: str = "1.0"


class ReportFormatter(ABC):
    """Abstract base class for report formatters."""
    
    @abstractmethod
    def format(self, result: ComparisonResult, metadata: ReportMetadata) -> str:
        """Format comparison result into specific output format.
        
        Args:
            result: ComparisonResult from audit
            metadata: Report metadata
            
        Returns:
            Formatted report as string
        """
        pass
    
    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension for this format."""
        pass


class MarkdownFormatter(ReportFormatter):
    """Markdown report formatter with structured sections."""
    
    def __init__(self, include_emoji: bool = True, detailed_items: bool = True):
        """Initialize markdown formatter.
        
        Args:
            include_emoji: Whether to include emojis in output
            detailed_items: Whether to include detailed item listings
        """
        self.include_emoji = include_emoji
        self.detailed_items = detailed_items
    
    @property
    def file_extension(self) -> str:
        return ".md"
    
    def format(self, result: ComparisonResult, metadata: ReportMetadata) -> str:
        """Format the comparison result as markdown."""
        lines = []
        
        # Header
        lines.extend(self._format_header(metadata))
        lines.append("")
        
        # Summary
        lines.extend(self._format_summary(result, metadata))
        lines.append("")
        
        # Project Overview (new project-centric format)
        lines.extend(self._format_projects_overview(result))
        lines.append("")
        
        # Recommendations
        lines.extend(self._format_recommendations(result))
        
        return "\n".join(lines)
    
    def _format_header(self, metadata: ReportMetadata) -> List[str]:
        """Format report header."""
        emoji = "📊 " if self.include_emoji else ""
        return [
            f"# {emoji}PARA Audit Report",
            "",
            f"**Generated:** {metadata.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Version:** {metadata.version}",
            f"**Sources:** {', '.join(metadata.sources_audited)}"
        ]
    
    def _format_summary(self, result: ComparisonResult, metadata: ReportMetadata) -> List[str]:
        """Format executive summary."""
        emoji = "📋 " if self.include_emoji else ""
        score_emoji = self._get_score_emoji(result.consistency_score)
        
        # Calculate project-specific stats
        todoist_projects = []
        for group in result.item_groups:
            for item in group:
                if item.source == ItemSource.TODOIST and item.type == ItemType.PROJECT:
                    todoist_projects.append(item)
        
        projects_with_next_actions = sum(1 for p in todoist_projects if p.metadata.get('has_next_action', False))
        total_next_action_tasks = sum(p.metadata.get('next_action_count', 0) for p in todoist_projects)
        
        lines = [
            f"## {emoji}Executive Summary",
            "",
            f"**Generated:** {metadata.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Sources:** {', '.join(metadata.sources_audited)}",
            "",
            f"**Consistency Score:** {score_emoji} {result.consistency_score:.1%}",
            f"**Projects Analyzed:** {len(todoist_projects)}",
            f"**Projects with Next Actions:** {projects_with_next_actions}/{len(todoist_projects)} ({100*projects_with_next_actions/len(todoist_projects) if todoist_projects else 0:.1f}%)",
            f"**Total Next Action Tasks:** {total_next_action_tasks}",
            f"**Remediations Needed:** {len(result.inconsistencies)}",
            ""
        ]
        
        return lines
    
    def _format_projects_overview(self, result: ComparisonResult) -> List[str]:
        """Format the new project-centric overview section."""
        lines = [
            "## 📊 Project Overview",
            "",
            "*Projects listed with their next actions and any required remediations.*",
            ""
        ]
        
        # Get all Todoist projects from item groups
        projects = []
        for group in result.item_groups:
            for item in group:
                if item.source == ItemSource.TODOIST and item.type == ItemType.PROJECT:
                    projects.append((item, group))
        
        # Sort projects by category (work/personal) and then by name
        projects.sort(key=lambda x: (x[0].category.value, x[0].raw_name or x[0].name))
        
        current_category = None
        for project, group in projects:
            # Add category headers
            if current_category != project.category.value:
                current_category = project.category.value
                category_emoji = "💼" if current_category == "work" else "🏠"
                lines.append(f"### {category_emoji} {current_category.title()} Projects")
                lines.append("")
            
            project_name = project.raw_name or project.name
            has_next_action = project.metadata.get('has_next_action', False)
            next_action_count = project.metadata.get('next_action_count', 0)
            next_action_label = project.metadata.get('next_action_label', 'next')
            next_action_tasks = project.metadata.get('next_action_tasks', [])
            
            # Project header
            lines.append(f"#### {project_name}")
            lines.append("")
            
            # Next action status
            if has_next_action:
                next_action_emoji = "⏭️" if self.include_emoji else ""
                lines.append(f"**{next_action_emoji} Next Actions:**")
                for task_name in next_action_tasks:
                    task_emoji = "  • " if not self.include_emoji else "  ⏭️ "
                    lines.append(f"{task_emoji}{task_name}")
            else:
                missing_emoji = "❌" if self.include_emoji else ""
                lines.append(f"**{missing_emoji} Missing Next Action**")
                lines.append(f"  • Add at least one task with @{next_action_label} label")
            
            lines.append("")
            
            # Find remediations for this project
            project_remediations = []
            for inc in result.inconsistencies:
                # Check if this inconsistency affects this project
                if inc.items and any(item.source == ItemSource.TODOIST and 
                                   (item.raw_name or item.name) == project_name for item in inc.items):
                    project_remediations.append(inc)
            
            # Display remediations
            if project_remediations:
                lines.append("**Remediations Needed:**")
                for inc in project_remediations:
                    severity_emoji = self._get_severity_emoji(inc.severity)
                    lines.append(f"  • {severity_emoji} {inc.description}")
                    lines.append(f"    *Action:* {inc.suggested_action}")
                lines.append("")
            else:
                lines.append("**Status:** ✅ No remediations needed")
                lines.append("")
        
        return lines
    
    def _format_statistics(self, result: ComparisonResult, metadata: ReportMetadata) -> List[str]:
        """Format statistics section."""
        emoji = "📈 " if self.include_emoji else ""
        lines = [
            f"## {emoji}Statistics",
            ""
        ]
        
        # Items by source
        source_counts = {}
        for group in result.item_groups:
            for item in group:
                source = item.source.value
                source_counts[source] = source_counts.get(source, 0) + 1
        
        lines.append("### Items by Source")
        lines.append("")
        for source, count in sorted(source_counts.items()):
            lines.append(f"- **{source.replace('_', ' ').title()}:** {count}")
        
        lines.append("")
        
        # Items by type
        type_counts = {'Project': 0, 'Area': 0}
        category_counts = {'Work': 0, 'Personal': 0}
        
        for group in result.item_groups:
            for item in group:
                type_counts[item.type.value] += 1
                category_counts[item.category.value.title()] += 1
        
        lines.append("### Items by Type")
        lines.append("")
        for item_type, count in type_counts.items():
            type_emoji = "🎯" if item_type == "Project" else "📁"
            lines.append(f"- {type_emoji} **{item_type}:** {count}")
        
        lines.append("")
        lines.append("### Items by Category")
        lines.append("")
        for category, count in category_counts.items():
            cat_emoji = "💼" if category == "Work" else "🏠"
            lines.append(f"- {cat_emoji} **{category}:** {count}")
        
        # Next action statistics
        next_action_stats = self._calculate_next_action_stats(result)
        if next_action_stats['total_projects'] > 0:
            lines.append("")
            lines.append("### Next Action Status")
            lines.append("")
            coverage_percent = (next_action_stats['projects_with_next_actions'] / next_action_stats['total_projects']) * 100
            lines.append(f"- ⏭️ **Projects with next actions:** {next_action_stats['projects_with_next_actions']}/{next_action_stats['total_projects']} ({coverage_percent:.1f}%)")
            if next_action_stats['projects_without_next_actions'] > 0:
                lines.append(f"- ❌ **Projects missing next actions:** {next_action_stats['projects_without_next_actions']}")
            lines.append(f"- 📋 **Total next action tasks:** {next_action_stats['total_next_action_tasks']}")
            if next_action_stats['next_action_labels_used']:
                labels_list = ', '.join(f"@{label}" for label in next_action_stats['next_action_labels_used'])
                lines.append(f"- 🏷️ **Labels used:** {labels_list}")
        
        return lines
    
    def _format_recommendations(self, result: ComparisonResult) -> List[str]:
        """Format recommendations section."""
        emoji = "💡 " if self.include_emoji else ""
        lines = [
            f"## {emoji}Recommendations",
            ""
        ]
        
        if result.consistency_score >= 0.9:
            lines.append("🎉 **Excellent consistency!** Your PARA organization is well-maintained.")
        elif result.consistency_score >= 0.7:
            lines.append("👍 **Good consistency** with some areas for improvement.")
        else:
            lines.append("⚠️ **Significant inconsistencies detected** - consider cleanup.")
        
        lines.append("")
        
        # Specific recommendations based on inconsistencies
        high_priority = [inc for inc in result.inconsistencies if inc.severity == 'high']
        if high_priority:
            lines.append("### High Priority Actions")
            lines.append("")
            for inc in high_priority[:5]:  # Top 5
                lines.append(f"1. {inc.suggested_action}")
            lines.append("")
        
        # General recommendations
        lines.extend([
            "### General Best Practices",
            "",
            "- Regularly review and update project status (active/inactive)",
            "- Maintain consistent naming across all tools",
            "- Use emoji prefixes for visual organization",
            "- Keep work and personal items in appropriate accounts",
            "- Link Todoist projects to relevant Google Drive folders"
        ])
        
        return lines
    
    def _calculate_next_action_stats(self, result: ComparisonResult) -> Dict[str, Any]:
        """Calculate next action statistics for Todoist projects."""
        stats = {
            'total_projects': 0,
            'projects_with_next_actions': 0,
            'projects_without_next_actions': 0,
            'total_next_action_tasks': 0,
            'next_action_labels_used': set()
        }
        
        for group in result.item_groups:
            for item in group:
                if item.source == ItemSource.TODOIST and item.type == ItemType.PROJECT:
                    stats['total_projects'] += 1
                    has_next_action = item.metadata.get('has_next_action', False)
                    next_action_count = item.metadata.get('next_action_count', 0)
                    next_action_label = item.metadata.get('next_action_label', 'next')
                    
                    if has_next_action:
                        stats['projects_with_next_actions'] += 1
                        stats['total_next_action_tasks'] += next_action_count
                    else:
                        stats['projects_without_next_actions'] += 1
                    
                    stats['next_action_labels_used'].add(next_action_label)
        
        # Convert set to list for consistency
        stats['next_action_labels_used'] = list(stats['next_action_labels_used'])
        
        return stats
    
    def _get_score_emoji(self, score: float) -> str:
        """Get emoji for consistency score."""
        if not self.include_emoji:
            return ""
        if score >= 0.9:
            return "🟢"
        elif score >= 0.7:
            return "🟡"
        else:
            return "🔴"
    
    def _get_severity_emoji(self, severity: str) -> str:
        """Get emoji for severity level."""
        if not self.include_emoji:
            return ""
        return {
            'high': '🚨',
            'medium': '⚠️',
            'low': 'ℹ️'
        }.get(severity, '❓')
    
    def _get_inconsistency_emoji(self, inc_type: InconsistencyType) -> str:
        """Get emoji for inconsistency type."""
        if not self.include_emoji:
            return ""
        return {
            InconsistencyType.MISSING_ITEM: '❌',
            InconsistencyType.STATUS_MISMATCH: '🔄',
            InconsistencyType.TYPE_MISMATCH: '🏷️',
            InconsistencyType.CATEGORY_MISMATCH: '📊',
            InconsistencyType.WRONG_ACCOUNT: '👤',
            InconsistencyType.DUPLICATE_ITEM: '👥',
            InconsistencyType.NAME_VARIATION: '📝',
            InconsistencyType.MISSING_EMOJI: '😐',
            InconsistencyType.MISSING_NEXT_ACTION: '⏭️'
        }.get(inc_type, '❓')
    
    def _get_source_emoji(self, source: ItemSource) -> str:
        """Get emoji for item source."""
        if not self.include_emoji:
            return ""
        return {
            ItemSource.TODOIST: '✅',
            ItemSource.APPLE_NOTES: '📝',
            ItemSource.GDRIVE_WORK: '💼',
            ItemSource.GDRIVE_PERSONAL: '🏠'
        }.get(source, '❓')


class JSONFormatter(ReportFormatter):
    """JSON report formatter for programmatic access."""
    
    def __init__(self, pretty_print: bool = True):
        """Initialize JSON formatter.
        
        Args:
            pretty_print: Whether to format JSON with indentation
        """
        self.pretty_print = pretty_print
    
    @property
    def file_extension(self) -> str:
        return ".json"
    
    def format(self, result: ComparisonResult, metadata: ReportMetadata) -> str:
        """Format as JSON report."""
        report_data = {
            'metadata': {
                'generated_at': metadata.generated_at.isoformat(),
                'version': metadata.version,
                'total_items': metadata.total_items,
                'consistency_score': metadata.consistency_score,
                'sources_audited': metadata.sources_audited,
                'filters_applied': metadata.filters_applied
            },
            'summary': {
                'total_items': result.total_items,
                'consistent_items': result.consistent_items,
                'consistency_score': result.consistency_score,
                'total_inconsistencies': len(result.inconsistencies),
                'high_severity_count': result.high_severity_count,
                'medium_severity_count': result.medium_severity_count,
                'low_severity_count': result.low_severity_count
            },
            'inconsistencies': [
                {
                    'type': inc.type.value,
                    'description': inc.description,
                    'severity': inc.severity,
                    'suggested_action': inc.suggested_action,
                    'affected_items': [
                        {
                            'name': item.name,
                            'raw_name': item.raw_name,
                            'type': item.type.value,
                            'is_active': item.is_active,
                            'category': item.category.value,
                            'source': item.source.value,
                            'metadata': item.metadata
                        }
                        for item in inc.items
                    ],
                    'metadata': inc.metadata
                }
                for inc in result.inconsistencies
            ],
            'item_groups': [
                [
                    {
                        'name': item.name,
                        'raw_name': item.raw_name,
                        'type': item.type.value,
                        'is_active': item.is_active,
                        'category': item.category.value,
                        'source': item.source.value,
                        'has_emoji': item.has_emoji(),
                        'metadata': item.metadata
                    }
                    for item in group
                ]
                for group in result.item_groups
            ],
            'orphaned_items': [
                {
                    'name': item.name,
                    'raw_name': item.raw_name,
                    'type': item.type.value,
                    'is_active': item.is_active,
                    'category': item.category.value,
                    'source': item.source.value,
                    'has_emoji': item.has_emoji(),
                    'metadata': item.metadata
                }
                for item in result.orphaned_items
            ],
            'statistics': self._calculate_statistics(result)
        }
        
        if self.pretty_print:
            return json.dumps(report_data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(report_data, separators=(',', ':'), ensure_ascii=False)
    
    def _calculate_statistics(self, result: ComparisonResult) -> Dict[str, Any]:
        """Calculate detailed statistics for JSON output."""
        # Count by source
        source_counts = {}
        for group in result.item_groups:
            for item in group:
                source = item.source.value
                source_counts[source] = source_counts.get(source, 0) + 1
        
        # Count by type and category
        type_counts = {'project': 0, 'area': 0}
        category_counts = {'work': 0, 'personal': 0}
        emoji_counts = {'with_emoji': 0, 'without_emoji': 0}
        
        for group in result.item_groups:
            for item in group:
                type_counts[item.type.value.lower()] += 1
                category_counts[item.category.value] += 1
                if item.has_emoji():
                    emoji_counts['with_emoji'] += 1
                else:
                    emoji_counts['without_emoji'] += 1
        
        # Inconsistency type counts
        inconsistency_counts = {}
        for inc in result.inconsistencies:
            inc_type = inc.type.value
            inconsistency_counts[inc_type] = inconsistency_counts.get(inc_type, 0) + 1
        
        # Next action statistics
        next_action_stats = {
            'projects_with_next_actions': 0,
            'projects_without_next_actions': 0,
            'total_next_action_tasks': 0,
            'next_action_labels_used': set()
        }
        
        for group in result.item_groups:
            for item in group:
                if item.source.value == 'todoist' and item.type.value == 'project':
                    has_next_action = item.metadata.get('has_next_action', False)
                    next_action_count = item.metadata.get('next_action_count', 0)
                    next_action_label = item.metadata.get('next_action_label', 'next')
                    
                    if has_next_action:
                        next_action_stats['projects_with_next_actions'] += 1
                        next_action_stats['total_next_action_tasks'] += next_action_count
                    else:
                        next_action_stats['projects_without_next_actions'] += 1
                    
                    next_action_stats['next_action_labels_used'].add(next_action_label)
        
        # Convert set to list for JSON serialization
        next_action_stats['next_action_labels_used'] = list(next_action_stats['next_action_labels_used'])
        
        return {
            'items_by_source': source_counts,
            'items_by_type': type_counts,
            'items_by_category': category_counts,
            'emoji_usage': emoji_counts,
            'inconsistencies_by_type': inconsistency_counts,
            'orphaned_items_count': len(result.orphaned_items),
            'item_groups_count': len(result.item_groups),
            'next_action_stats': next_action_stats
        }


class TextFormatter(ReportFormatter):
    """Plain text report formatter for console output."""
    
    def __init__(self, width: int = 80, include_details: bool = True):
        """Initialize text formatter.
        
        Args:
            width: Maximum line width for formatting
            include_details: Whether to include detailed sections
        """
        self.width = width
        self.include_details = include_details
    
    @property
    def file_extension(self) -> str:
        return ".txt"
    
    def format(self, result: ComparisonResult, metadata: ReportMetadata) -> str:
        """Format as plain text report."""
        lines = []
        
        # Header
        lines.extend(self._format_header(metadata))
        lines.append("")
        
        # Summary
        lines.extend(self._format_summary(result))
        lines.append("")
        
        # Issues (if any)
        if result.inconsistencies and self.include_details:
            lines.extend(self._format_issues(result.inconsistencies))
            lines.append("")
        
        # Quick stats
        lines.extend(self._format_quick_stats(result))
        
        return "\n".join(lines)
    
    def _format_header(self, metadata: ReportMetadata) -> List[str]:
        """Format text header."""
        title = "PARA AUDIT REPORT"
        border = "=" * len(title)
        
        return [
            border,
            title,
            border,
            "",
            f"Generated: {metadata.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Sources: {', '.join(metadata.sources_audited)}"
        ]
    
    def _format_summary(self, result: ComparisonResult) -> List[str]:
        """Format summary section."""
        score_indicator = self._get_score_indicator(result.consistency_score)
        
        return [
            "SUMMARY",
            "-" * 7,
            "",
            f"Consistency Score: {result.consistency_score:.1%} {score_indicator}",
            f"Total Items: {result.total_items}",
            f"Consistent Items: {result.consistent_items}",
            f"Issues Found: {len(result.inconsistencies)}",
            "",
            f"High Priority: {result.high_severity_count}",
            f"Medium Priority: {result.medium_severity_count}",
            f"Low Priority: {result.low_severity_count}"
        ]
    
    def _format_issues(self, inconsistencies: List[Inconsistency]) -> List[str]:
        """Format issues section."""
        lines = [
            "ISSUES FOUND",
            "-" * 12,
            ""
        ]
        
        for i, inc in enumerate(inconsistencies[:10], 1):  # Top 10 issues
            severity_indicator = self._get_severity_indicator(inc.severity)
            lines.extend([
                f"{i}. [{severity_indicator}] {inc.description}",
                f"   Action: {inc.suggested_action}",
                ""
            ])
        
        if len(inconsistencies) > 10:
            lines.append(f"... and {len(inconsistencies) - 10} more issues")
        
        return lines
    
    def _format_quick_stats(self, result: ComparisonResult) -> List[str]:
        """Format quick statistics."""
        # Count by source
        source_counts = {}
        for group in result.item_groups:
            for item in group:
                source = item.source.value.replace('_', ' ').title()
                source_counts[source] = source_counts.get(source, 0) + 1
        
        lines = [
            "QUICK STATS",
            "-" * 11,
            ""
        ]
        
        for source, count in sorted(source_counts.items()):
            lines.append(f"{source}: {count} items")
        
        return lines
    
    def _get_score_indicator(self, score: float) -> str:
        """Get text indicator for consistency score."""
        if score >= 0.9:
            return "[EXCELLENT]"
        elif score >= 0.7:
            return "[GOOD]"
        elif score >= 0.5:
            return "[FAIR]"
        else:
            return "[NEEDS WORK]"
    
    def _get_severity_indicator(self, severity: str) -> str:
        """Get text indicator for severity."""
        return {
            'high': 'HIGH',
            'medium': 'MED',
            'low': 'LOW'
        }.get(severity, 'UNK')


class ReportGenerator:
    """Main report generator with support for multiple output formats."""
    
    def __init__(self):
        """Initialize report generator."""
        self.formatters = {
            'markdown': MarkdownFormatter(),
            'json': JSONFormatter(),
            'text': TextFormatter()
        }
    
    def generate_report(
        self,
        result: ComparisonResult,
        format_type: str = 'markdown',
        output_path: Optional[Union[str, Path]] = None,
        metadata_overrides: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate audit report in specified format.
        
        Args:
            result: ComparisonResult from audit
            format_type: Output format ('markdown', 'json', 'text')
            output_path: Optional path to save report
            metadata_overrides: Optional metadata overrides
            
        Returns:
            Formatted report as string
            
        Raises:
            ValueError: If format_type is not supported
        """
        if format_type not in self.formatters:
            available = ", ".join(self.formatters.keys())
            raise ValueError(f"Unsupported format '{format_type}'. Available: {available}")
        
        # Create metadata
        metadata = ReportMetadata(
            generated_at=datetime.now(),
            total_items=result.total_items,
            consistency_score=result.consistency_score,
            sources_audited=self._extract_sources(result),
            filters_applied=metadata_overrides.get('filters_applied', {}) if metadata_overrides else {}
        )
        
        # Apply metadata overrides
        if metadata_overrides:
            for key, value in metadata_overrides.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)
        
        # Generate report
        formatter = self.formatters[format_type]
        report_content = formatter.format(result, metadata)
        
        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            if output_path.suffix == "":
                output_path = output_path.with_suffix(formatter.file_extension)
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_content, encoding='utf-8')
            logger.info(f"Report saved to {output_path}")
        
        return report_content
    
    def _extract_sources(self, result: ComparisonResult) -> List[str]:
        """Extract unique sources from comparison result."""
        sources = set()
        for group in result.item_groups:
            for item in group:
                sources.add(item.source.value.replace('_', ' ').title())
        
        for item in result.orphaned_items:
            sources.add(item.source.value.replace('_', ' ').title())
        
        return sorted(list(sources))
    
    def add_formatter(self, name: str, formatter: ReportFormatter) -> None:
        """Add custom formatter.
        
        Args:
            name: Name for the formatter
            formatter: ReportFormatter instance
        """
        self.formatters[name] = formatter
    
    def get_available_formats(self) -> List[str]:
        """Get list of available report formats.
        
        Returns:
            List of format names
        """
        return list(self.formatters.keys())
    
    def generate_all_formats(
        self,
        result: ComparisonResult,
        output_dir: Union[str, Path],
        base_filename: str = "para_audit_report",
        metadata_overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Path]:
        """Generate reports in all available formats.
        
        Args:
            result: ComparisonResult from audit
            output_dir: Directory to save reports
            base_filename: Base filename (without extension)
            metadata_overrides: Optional metadata overrides
            
        Returns:
            Dictionary mapping format names to output file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = {}
        
        for format_name, formatter in self.formatters.items():
            output_path = output_dir / f"{base_filename}{formatter.file_extension}"
            
            self.generate_report(
                result=result,
                format_type=format_name,
                output_path=output_path,
                metadata_overrides=metadata_overrides
            )
            
            generated_files[format_name] = output_path
        
        return generated_files
