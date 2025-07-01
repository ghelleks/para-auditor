"""Item comparison logic for cross-tool PARA method consistency checking."""
import logging
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from ..models.para_item import PARAItem, ItemType, ItemSource, CategoryType
from ..utils.name_matcher import NameMatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InconsistencyType(Enum):
    """Types of inconsistencies that can be detected."""
    MISSING_ITEM = "missing_item"
    STATUS_MISMATCH = "status_mismatch"
    TYPE_MISMATCH = "type_mismatch"
    CATEGORY_MISMATCH = "category_mismatch"
    WRONG_ACCOUNT = "wrong_account"
    DUPLICATE_ITEM = "duplicate_item"
    NAME_VARIATION = "name_variation"
    MISSING_EMOJI = "missing_emoji"


@dataclass
class Inconsistency:
    """Represents an inconsistency found during comparison."""
    type: InconsistencyType
    description: str
    severity: str  # 'high', 'medium', 'low'
    items: List[PARAItem]
    suggested_action: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ComparisonResult:
    """Results of comparing PARA items across tools."""
    total_items: int
    consistent_items: int
    inconsistencies: List[Inconsistency]
    item_groups: List[List[PARAItem]]  # Groups of matching items
    orphaned_items: List[PARAItem]  # Items with no matches
    
    @property
    def consistency_score(self) -> float:
        """Calculate overall consistency score (0.0 to 1.0)."""
        if self.total_items == 0:
            return 1.0
        return self.consistent_items / self.total_items
    
    @property
    def high_severity_count(self) -> int:
        """Count of high severity inconsistencies."""
        return sum(1 for inc in self.inconsistencies if inc.severity == 'high')
    
    @property
    def medium_severity_count(self) -> int:
        """Count of medium severity inconsistencies."""
        return sum(1 for inc in self.inconsistencies if inc.severity == 'medium')
    
    @property
    def low_severity_count(self) -> int:
        """Count of low severity inconsistencies."""
        return sum(1 for inc in self.inconsistencies if inc.severity == 'low')


class ItemComparator:
    """Compares PARA items across different tools to identify inconsistencies."""
    
    def __init__(self, similarity_threshold: float = 0.8, strict_mode: bool = False):
        """Initialize item comparator.
        
        Args:
            similarity_threshold: Threshold for name matching
            strict_mode: If True, applies stricter validation rules
        """
        self.similarity_threshold = similarity_threshold
        self.strict_mode = strict_mode
        self.name_matcher = NameMatcher(similarity_threshold)
        
    def compare_items(self, items: List[PARAItem]) -> ComparisonResult:
        """Compare PARA items across tools and identify inconsistencies.
        
        Args:
            items: List of PARAItem objects from all sources
            
        Returns:
            ComparisonResult with detailed analysis
        """
        logger.info(f"Comparing {len(items)} PARA items across tools")
        
        # Group items by similarity
        item_groups = self._group_similar_items(items)
        
        # Propagate categories from Todoist to matching items
        self._propagate_categories_from_todoist(item_groups)
        
        # Find orphaned items (no matches across tools)
        orphaned_items = self._find_orphaned_items(item_groups)
        
        # Detect inconsistencies
        inconsistencies = []
        consistent_items = 0
        
        for group in item_groups:
            group_inconsistencies = self._analyze_item_group(group)
            inconsistencies.extend(group_inconsistencies)
            
            if not group_inconsistencies:
                consistent_items += len(group)
        
        # Add orphaned item inconsistencies
        for item in orphaned_items:
            inconsistencies.append(Inconsistency(
                type=InconsistencyType.MISSING_ITEM,
                description=f"'{item.name}' exists only in {item.source.value}",
                severity='medium',
                items=[item],
                suggested_action=f"Add '{item.name}' to other tools or verify it should exist",
                metadata={'source': item.source.value}
            ))
        
        return ComparisonResult(
            total_items=len(items),
            consistent_items=consistent_items,
            inconsistencies=inconsistencies,
            item_groups=item_groups,
            orphaned_items=orphaned_items
        )
    
    def _group_similar_items(self, items: List[PARAItem]) -> List[List[PARAItem]]:
        """Group similar items together based on name matching.
        
        Args:
            items: List of PARAItem objects
            
        Returns:
            List of groups, each containing similar items
        """
        groups = []
        processed = set()
        
        for item in items:
            if id(item) in processed:
                continue
            
            # Start new group
            current_group = [item]
            processed.add(id(item))
            
            # Find similar items
            for other_item in items:
                if id(other_item) not in processed:
                    if self.name_matcher.is_match(item.name, other_item.name):
                        current_group.append(other_item)
                        processed.add(id(other_item))
            
            groups.append(current_group)
        
        return groups
    
    def _propagate_categories_from_todoist(self, item_groups: List[List[PARAItem]]) -> None:
        """Propagate work/personal categories from Todoist items to their matching items.
        
        Todoist projects with 💼 prefix are authoritative for work/personal classification.
        This method updates Apple Notes and Google Drive items to match Todoist category.
        
        Args:
            item_groups: List of grouped similar items
        """
        for group in item_groups:
            # Find Todoist item in this group (if any)
            todoist_item = None
            for item in group:
                if item.source == ItemSource.TODOIST:
                    todoist_item = item
                    break
            
            # If we have a Todoist item, propagate its category to other items
            if todoist_item:
                for item in group:
                    if item.source != ItemSource.TODOIST:
                        # Update the category to match Todoist
                        item.category = todoist_item.category
    
    def _find_orphaned_items(self, item_groups: List[List[PARAItem]]) -> List[PARAItem]:
        """Find items that don't have matches in other tools.
        
        Args:
            item_groups: Grouped items
            
        Returns:
            List of orphaned items
        """
        orphaned = []
        
        for group in item_groups:
            if len(group) == 1:
                # Check if this item has potential matches in other sources
                item = group[0]
                sources_in_group = {item.source}
                
                # An item is orphaned if it's the only one from its source
                # and there are other sources that should have it
                if len(sources_in_group) == 1:
                    orphaned.append(item)
        
        return orphaned
    
    def _analyze_item_group(self, group: List[PARAItem]) -> List[Inconsistency]:
        """Analyze a group of similar items for inconsistencies.
        
        Args:
            group: List of similar PARAItem objects
            
        Returns:
            List of inconsistencies found in the group
        """
        if len(group) <= 1:
            return []
        
        inconsistencies = []
        
        # Check for status inconsistencies
        inconsistencies.extend(self._check_status_consistency(group))
        
        # Check for type inconsistencies
        inconsistencies.extend(self._check_type_consistency(group))
        
        # Check for category inconsistencies
        inconsistencies.extend(self._check_category_consistency(group))
        
        # Check for account placement issues
        inconsistencies.extend(self._check_account_placement(group))
        
        
        # Check for name variations
        inconsistencies.extend(self._check_name_variations(group))
        
        # Check for emoji consistency
        inconsistencies.extend(self._check_emoji_consistency(group))
        
        return inconsistencies
    
    def _check_status_consistency(self, group: List[PARAItem]) -> List[Inconsistency]:
        """Check for active/inactive status inconsistencies.
        
        Args:
            group: Group of similar items
            
        Returns:
            List of status inconsistencies
        """
        inconsistencies = []
        
        active_items = [item for item in group if item.is_active]
        inactive_items = [item for item in group if not item.is_active]
        
        if active_items and inactive_items:
            # Mixed active/inactive status
            active_sources = [item.source.value for item in active_items]
            inactive_sources = [item.source.value for item in inactive_items]
            
            inconsistencies.append(Inconsistency(
                type=InconsistencyType.STATUS_MISMATCH,
                description=f"'{group[0].name}' is active in {active_sources} but inactive in {inactive_sources}",
                severity='high',
                items=group,
                suggested_action="Decide whether this should be active or inactive and update all tools",
                metadata={
                    'active_sources': active_sources,
                    'inactive_sources': inactive_sources
                }
            ))
        
        return inconsistencies
    
    def _check_type_consistency(self, group: List[PARAItem]) -> List[Inconsistency]:
        """Check for Project/Area type inconsistencies.
        
        Args:
            group: Group of similar items
            
        Returns:
            List of type inconsistencies
        """
        inconsistencies = []
        
        types = set(item.type for item in group)
        if len(types) > 1:
            type_sources = {}
            for item in group:
                if item.type not in type_sources:
                    type_sources[item.type] = []
                type_sources[item.type].append(item.source.value)
            
            type_desc = ", ".join([f"{t.value} in {sources}" for t, sources in type_sources.items()])
            
            inconsistencies.append(Inconsistency(
                type=InconsistencyType.TYPE_MISMATCH,
                description=f"'{group[0].name}' has different types: {type_desc}",
                severity='high',
                items=group,
                suggested_action="Standardize whether this should be a Project or Area across all tools",
                metadata={'type_sources': {t.value: sources for t, sources in type_sources.items()}}
            ))
        
        return inconsistencies
    
    def _check_category_consistency(self, group: List[PARAItem]) -> List[Inconsistency]:
        """Check for work/personal category inconsistencies.
        
        Args:
            group: Group of similar items
            
        Returns:
            List of category inconsistencies
        """
        inconsistencies = []
        
        categories = set(item.category for item in group)
        if len(categories) > 1:
            category_sources = {}
            for item in group:
                if item.category not in category_sources:
                    category_sources[item.category] = []
                category_sources[item.category].append(item.source.value)
            
            category_desc = ", ".join([f"{c.value} in {sources}" for c, sources in category_sources.items()])
            
            inconsistencies.append(Inconsistency(
                type=InconsistencyType.CATEGORY_MISMATCH,
                description=f"'{group[0].name}' has different categories: {category_desc}",
                severity='medium',
                items=group,
                suggested_action="Verify and standardize whether this is work or personal",
                metadata={'category_sources': {c.value: sources for c, sources in category_sources.items()}}
            ))
        
        return inconsistencies
    
    def _check_account_placement(self, group: List[PARAItem]) -> List[Inconsistency]:
        """Check for incorrect Google Drive account placement.
        
        Args:
            group: Group of similar items
            
        Returns:
            List of account placement inconsistencies
        """
        inconsistencies = []
        
        # Find Todoist and Google Drive items
        todoist_items = [item for item in group if item.source == ItemSource.TODOIST]
        gdrive_work_items = [item for item in group if item.source == ItemSource.GDRIVE_WORK]
        gdrive_personal_items = [item for item in group if item.source == ItemSource.GDRIVE_PERSONAL]
        
        for todoist_item in todoist_items:
            expected_category = todoist_item.category
            
            # Check if item is in wrong Google Drive account
            if expected_category == CategoryType.WORK and gdrive_personal_items:
                inconsistencies.append(Inconsistency(
                    type=InconsistencyType.WRONG_ACCOUNT,
                    description=f"'{todoist_item.name}' is marked as work but found in personal Google Drive",
                    severity='high',
                    items=[todoist_item] + gdrive_personal_items,
                    suggested_action="Move to work Google Drive account or update category",
                    metadata={'expected_account': 'work', 'actual_account': 'personal'}
                ))
            
            elif expected_category == CategoryType.PERSONAL and gdrive_work_items:
                inconsistencies.append(Inconsistency(
                    type=InconsistencyType.WRONG_ACCOUNT,
                    description=f"'{todoist_item.name}' is marked as personal but found in work Google Drive",
                    severity='high',
                    items=[todoist_item] + gdrive_work_items,
                    suggested_action="Move to personal Google Drive account or update category",
                    metadata={'expected_account': 'personal', 'actual_account': 'work'}
                ))
        
        return inconsistencies
    
    
    def _check_name_variations(self, group: List[PARAItem]) -> List[Inconsistency]:
        """Check for name variations within a group.
        
        Args:
            group: Group of similar items
            
        Returns:
            List of name variation inconsistencies
        """
        inconsistencies = []
        
        if len(group) <= 1:
            return inconsistencies
        
        # Check if names are exactly the same
        unique_names = set(item.raw_name or item.name for item in group)
        
        if len(unique_names) > 1:
            # Names vary - suggest canonical name
            canonical_name = self.name_matcher.suggest_canonical_name(list(unique_names))
            
            name_variations = {}
            for item in group:
                name = item.raw_name or item.name
                if name != canonical_name:
                    if name not in name_variations:
                        name_variations[name] = []
                    name_variations[name].append(item.source.value)
            
            if name_variations:
                variations_desc = ", ".join([f"'{name}' in {sources}" for name, sources in name_variations.items()])
                
                inconsistencies.append(Inconsistency(
                    type=InconsistencyType.NAME_VARIATION,
                    description=f"Name variations found: {variations_desc}",
                    severity='low',
                    items=group,
                    suggested_action=f"Standardize name to '{canonical_name}' across all tools",
                    metadata={
                        'canonical_name': canonical_name,
                        'variations': name_variations
                    }
                ))
        
        return inconsistencies
    
    def _check_emoji_consistency(self, group: List[PARAItem]) -> List[Inconsistency]:
        """Check for emoji consistency across tools.
        
        Args:
            group: Group of similar items
            
        Returns:
            List of emoji inconsistencies
        """
        inconsistencies = []
        
        emoji_items = [item for item in group if item.has_emoji()]
        non_emoji_items = [item for item in group if not item.has_emoji()]
        
        if emoji_items and non_emoji_items:
            # Mixed emoji usage
            emoji_sources = [item.source.value for item in emoji_items]
            non_emoji_sources = [item.source.value for item in non_emoji_items]
            
            inconsistencies.append(Inconsistency(
                type=InconsistencyType.MISSING_EMOJI,
                description=f"'{group[0].name}' has emoji in {emoji_sources} but not in {non_emoji_sources}",
                severity='low',
                items=group,
                suggested_action="Add emoji prefix to items missing it for consistency",
                metadata={
                    'emoji_sources': emoji_sources,
                    'non_emoji_sources': non_emoji_sources
                }
            ))
        
        return inconsistencies
    
    def get_summary_statistics(self, result: ComparisonResult) -> Dict[str, Any]:
        """Generate summary statistics from comparison result.
        
        Args:
            result: ComparisonResult to summarize
            
        Returns:
            Dictionary with summary statistics
        """
        inconsistency_counts = {}
        for inc_type in InconsistencyType:
            inconsistency_counts[inc_type.value] = len([
                inc for inc in result.inconsistencies if inc.type == inc_type
            ])
        
        source_counts = {}
        for source in ItemSource:
            source_counts[source.value] = 0
        
        for group in result.item_groups:
            for item in group:
                source_counts[item.source.value] += 1
        
        return {
            'total_items': result.total_items,
            'consistent_items': result.consistent_items,
            'consistency_score': result.consistency_score,
            'total_inconsistencies': len(result.inconsistencies),
            'high_severity_count': result.high_severity_count,
            'medium_severity_count': result.medium_severity_count,
            'low_severity_count': result.low_severity_count,
            'inconsistency_types': inconsistency_counts,
            'items_per_source': source_counts,
            'orphaned_items_count': len(result.orphaned_items),
            'item_groups_count': len(result.item_groups)
        }
