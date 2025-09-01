"""Emoji detection and suggestion logic for PARA method items."""
import re
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from ..models.para_item import PARAItem, ItemType, CategoryType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmojiCategory(Enum):
    """Categories for emoji suggestions."""
    WORK = "work"
    PERSONAL = "personal"
    GENERAL = "general"
    PROJECT = "project"
    AREA = "area"


@dataclass
class EmojiSuggestion:
    """Represents an emoji suggestion for an item."""
    emoji: str
    reason: str
    confidence: float  # 0.0 to 1.0
    category: EmojiCategory
    keywords: List[str]


class EmojiSuggester:
    """Suggests appropriate emojis for PARA method items based on keywords and context."""
    
    def __init__(self):
        """Initialize emoji suggester with predefined mappings."""
        self._init_emoji_mappings()
        self._init_unicode_ranges()
    
    def _init_emoji_mappings(self):
        """Initialize keyword-to-emoji mappings."""
        # Work-related emojis
        self.work_emojis = {
            # Business & Office
            'business': ['💼', '🏢', '💻', '📊'],
            'office': ['🏢', '💼', '🖥️', '📋'],
            'meeting': ['👥', '🤝', '📅', '💬'],
            'project': ['📁', '🎯', '🔨', '⚡'],
            'admin': ['📋', '📝', '🗂️', '📊'],
            'finance': ['💰', '💳', '📈', '💹'],
            'hr': ['👥', '🤝', '👤', '📋'],
            'marketing': ['📢', '📈', '🎯', '💡'],
            'sales': ['💰', '🤝', '📈', '🎯'],
            'development': ['💻', '⚙️', '🔧', '🚀'],
            'design': ['🎨', '✏️', '🖌️', '📐'],
            'legal': ['⚖️', '📜', '🏛️', '📋'],
            'operations': ['⚙️', '🔧', '📊', '🔄'],
            'strategy': ['🎯', '📊', '🧭', '💡'],
            'planning': ['📅', '📋', '🗓️', '📝'],
            'communication': ['📞', '📧', '💬', '📢'],
            'training': ['🎓', '📚', '👨‍🏫', '📖'],
            'research': ['🔍', '📊', '🧪', '📈'],
            'client': ['🤝', '👥', '💼', '📞'],
            'customer': ['🤝', '😊', '💼', '⭐'],
            'team': ['👥', '🤝', '⚡', '🎯'],
            'leadership': ['👑', '🎯', '🧭', '⭐'],
            'management': ['👨‍💼', '📊', '⚙️', '🎯'],
            'budget': ['💰', '💳', '📊', '💹'],
            'report': ['📊', '📈', '📋', '📝'],
            'analysis': ['📊', '🔍', '📈', '🧮'],
            'compliance': ['✅', '⚖️', '📋', '🔍'],
            'security': ['🔒', '🛡️', '🔐', '⚠️'],
            'technology': ['💻', '⚙️', '🔧', '🚀'],
            'innovation': ['💡', '🚀', '⚡', '🌟'],
            'procurement': ['🛒', '📦', '💰', '🤝'],
            'vendor': ['🤝', '📦', '💼', '🔗'],
            'contract': ['📜', '✍️', '🤝', '⚖️'],
            'audit': ['🔍', '📋', '✅', '📊']
        }
        
        # Personal-related emojis
        self.personal_emojis = {
            # Life & Personal
            'health': ['🏥', '💊', '🩺', '❤️'],
            'fitness': ['💪', '🏃', '🏋️', '⚡'],
            'family': ['👨‍👩‍👧‍👦', '👪', '🏠', '❤️'],
            'home': ['🏠', '🏡', '🔧', '🛠️'],
            'travel': ['✈️', '🌍', '🗺️', '🎒'],
            'vacation': ['🏖️', '🌴', '✈️', '😎'],
            'hobby': ['🎨', '📚', '🎵', '🎮'],
            'learning': ['📚', '🎓', '💡', '🧠'],
            'education': ['🎓', '📚', '🏫', '📖'],
            'reading': ['📚', '📖', '📰', '👓'],
            'music': ['🎵', '🎼', '🎸', '🎤'],
            'cooking': ['👨‍🍳', '🍳', '🥘', '🍽️'],
            'gardening': ['🌱', '🌸', '🌿', '🏡'],
            'photography': ['📷', '📸', '🌅', '🎨'],
            'writing': ['✍️', '📝', '📚', '💭'],
            'creative': ['🎨', '✨', '💡', '🌟'],
            'social': ['👥', '🎉', '🍻', '😊'],
            'friends': ['👫', '🤗', '🎉', '💕'],
            'entertainment': ['🎬', '🎮', '🎪', '🎭'],
            'shopping': ['🛒', '🛍️', '💳', '🏪'],
            'car': ['🚗', '🔧', '⛽', '🚙'],
            'finance': ['💰', '💳', '🏦', '📊'],
            'investment': ['📈', '💹', '💰', '🏦'],
            'insurance': ['🛡️', '📋', '💼', '🏥'],
            'tax': ['💰', '📋', '🏛️', '📊'],
            'legal': ['⚖️', '📜', '🏛️', '📋'],
            'maintenance': ['🔧', '🛠️', '⚙️', '🏠'],
            'repair': ['🔧', '🛠️', '⚙️', '🔨'],
            'cleaning': ['🧹', '🧽', '🧴', '✨'],
            'organization': ['📁', '🗂️', '📋', '✅'],
            'planning': ['📅', '📋', '🗓️', '📝'],
            'goals': ['🎯', '⭐', '🏆', '📈'],
            'self': ['🧘', '💭', '🌟', '❤️'],
            'wellness': ['🧘', '💆', '🌿', '☮️'],
            'mindfulness': ['🧘', '☮️', '🌸', '💭'],
            'meditation': ['🧘', '☮️', '🕯️', '💭']
        }
        
        # General/neutral emojis
        self.general_emojis = {
            'idea': ['💡', '🌟', '✨', '🧠'],
            'important': ['⭐', '🌟', '❗', '🔥'],
            'urgent': ['🚨', '⚡', '🔥', '❗'],
            'complete': ['✅', '✔️', '🎉', '🏆'],
            'pending': ['⏳', '⏰', '🔄', '⏸️'],
            'archive': ['📦', '🗄️', '📁', '💾'],
            'reference': ['📚', '📖', '🔍', '📋'],
            'template': ['📋', '📝', '🗒️', '📄'],
            'process': ['⚙️', '🔄', '📊', '🎯'],
            'checklist': ['☑️', '📋', '✅', '📝'],
            'notes': ['📝', '🗒️', '💭', '📋'],
            'review': ['🔍', '👀', '📊', '✅'],
            'update': ['🔄', '📈', '⬆️', '🆕'],
            'new': ['🆕', '✨', '🌟', '⭐'],
            'old': ['📦', '🗄️', '⏳', '📜'],
            'draft': ['📝', '✏️', '📄', '🗒️'],
            'final': ['✅', '🏁', '🎯', '💯'],
            'backup': ['💾', '📦', '🔄', '🛡️'],
            'test': ['🧪', '🔬', '⚗️', '🧾'],
            'sample': ['📊', '🔍', '📈', '📋'],
            'example': ['💡', '👁️', '📋', '🔍'],
            'demo': ['🎬', '👁️', '💻', '📺'],
            'prototype': ['🔧', '⚙️', '🧪', '🚀'],
            'beta': ['🧪', '🚀', '⚡', '🔬'],
            'alpha': ['🚀', '⚡', '🧪', '🌟'],
            'launch': ['🚀', '🎉', '🌟', '⚡'],
            'release': ['🚀', '🎉', '📦', '✨']
        }
        
        # Combine all mappings
        self.all_mappings = {
            **self.work_emojis,
            **self.personal_emojis,
            **self.general_emojis
        }
    
    def _init_unicode_ranges(self):
        """Initialize Unicode ranges for emoji detection."""
        self.emoji_ranges = [
            (0x1F600, 0x1F64F),  # Emoticons
            (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
            (0x1F680, 0x1F6FF),  # Transport and Map
            (0x1F1E0, 0x1F1FF),  # Regional indicators
            (0x2600, 0x26FF),    # Misc symbols
            (0x2700, 0x27BF),    # Dingbats
            (0xFE00, 0xFE0F),    # Variation Selectors
            (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
            (0x1F018, 0x1F0F5),  # Mahjong tiles
            (0x1F000, 0x1F02F),  # Playing cards
        ]
    
    def detect_emoji(self, text: str) -> List[str]:
        """Detect emojis in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of emoji characters found
        """
        if not text:
            return []
        
        emojis = []
        for char in text:
            char_code = ord(char)
            if any(start <= char_code <= end for start, end in self.emoji_ranges):
                emojis.append(char)
        
        return emojis
    
    def has_emoji_prefix(self, text: str) -> bool:
        """Check if text starts with an emoji.
        
        Args:
            text: Text to check
            
        Returns:
            True if text starts with emoji
        """
        if not text:
            return False
        
        first_char = text[0]
        char_code = ord(first_char)
        return any(start <= char_code <= end for start, end in self.emoji_ranges)
    
    def extract_emoji_prefix(self, text: str) -> Optional[str]:
        """Extract emoji prefix from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Emoji prefix or None if not found
        """
        if not text or not self.has_emoji_prefix(text):
            return None
        
        # Find the end of emoji sequence
        i = 0
        while i < len(text):
            char_code = ord(text[i])
            is_emoji = any(start <= char_code <= end for start, end in self.emoji_ranges)
            if not is_emoji and text[i] not in [' ', '\u200d', '\ufe0f']:  # Not emoji, space, or modifier
                break
            i += 1
        
        return text[:i].strip()
    
    def suggest_emojis(self, item: PARAItem, max_suggestions: int = 3) -> List[EmojiSuggestion]:
        """Suggest appropriate emojis for a PARA item.
        
        Args:
            item: PARAItem to suggest emojis for
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of emoji suggestions
        """
        suggestions = []
        
        # If item already has emoji, return it as a suggestion
        if item.has_emoji():
            existing_emoji = self.extract_emoji_prefix(item.raw_name or item.name)
            if existing_emoji:
                suggestions.append(EmojiSuggestion(
                    emoji=existing_emoji,
                    reason="Already present",
                    confidence=1.0,
                    category=EmojiCategory.GENERAL,
                    keywords=[]
                ))
        
        # Analyze item name for keywords
        name_lower = (item.raw_name or item.name).lower()
        words = re.findall(r'\b\w+\b', name_lower)
        
        # Score potential emojis based on keyword matches
        emoji_scores = {}
        matched_keywords = set()
        
        for word in words:
            # Check for exact matches
            if word in self.all_mappings:
                matched_keywords.add(word)
                for emoji in self.all_mappings[word]:
                    if emoji not in emoji_scores:
                        emoji_scores[emoji] = []
                    emoji_scores[emoji].append((word, 1.0))
            
            # Check for partial matches
            for keyword, emojis in self.all_mappings.items():
                if word in keyword or keyword in word:
                    similarity = len(word) / max(len(word), len(keyword))
                    if similarity >= 0.6:  # Minimum similarity threshold
                        matched_keywords.add(keyword)
                        for emoji in emojis:
                            if emoji not in emoji_scores:
                                emoji_scores[emoji] = []
                            emoji_scores[emoji].append((keyword, similarity * 0.8))
        
        # Calculate final scores and create suggestions
        for emoji, matches in emoji_scores.items():
            total_score = sum(score for _, score in matches)
            avg_score = total_score / len(matches)
            
            # Boost score based on category relevance
            category_boost = self._get_category_boost(emoji, item)
            final_score = min(1.0, avg_score * category_boost)
            
            if final_score >= 0.3:  # Minimum confidence threshold
                category = self._classify_emoji_category(emoji, item)
                keywords = [keyword for keyword, _ in matches]
                
                suggestions.append(EmojiSuggestion(
                    emoji=emoji,
                    reason=f"Matches keywords: {', '.join(keywords)}",
                    confidence=final_score,
                    category=category,
                    keywords=keywords
                ))
        
        # Add default suggestions if no specific matches found
        if not suggestions or len(suggestions) < max_suggestions:
            default_suggestions = self._get_default_suggestions(item)
            suggestions.extend(default_suggestions)
        
        # Sort by confidence and return top suggestions
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions[:max_suggestions]
    
    def _get_category_boost(self, emoji: str, item: PARAItem) -> float:
        """Get category-specific boost for emoji relevance.
        
        Args:
            emoji: Emoji character
            item: PARAItem context
            
        Returns:
            Boost factor (1.0 = no boost, >1.0 = boost)
        """
        boost = 1.0
        
        # Check if emoji is in category-specific mappings
        if item.category == CategoryType.WORK:
            for emojis in self.work_emojis.values():
                if emoji in emojis:
                    boost = 1.3
                    break
        elif item.category == CategoryType.PERSONAL:
            for emojis in self.personal_emojis.values():
                if emoji in emojis:
                    boost = 1.3
                    break
        
        # Type-specific boost
        if item.type == ItemType.PROJECT:
            if emoji in ['🎯', '⚡', '🚀', '🔨', '⚙️']:
                boost *= 1.2
        elif item.type == ItemType.AREA:
            if emoji in ['📁', '🗂️', '📋', '🏠', '💼']:
                boost *= 1.2
        
        return boost
    
    def _classify_emoji_category(self, emoji: str, item: PARAItem) -> EmojiCategory:
        """Classify emoji into a category.
        
        Args:
            emoji: Emoji character
            item: PARAItem context
            
        Returns:
            EmojiCategory
        """
        # Check work emojis
        for emojis in self.work_emojis.values():
            if emoji in emojis:
                return EmojiCategory.WORK
        
        # Check personal emojis
        for emojis in self.personal_emojis.values():
            if emoji in emojis:
                return EmojiCategory.PERSONAL
        
        # Default based on item properties
        if item.type == ItemType.PROJECT:
            return EmojiCategory.PROJECT
        elif item.type == ItemType.AREA:
            return EmojiCategory.AREA
        else:
            return EmojiCategory.GENERAL
    
    def _get_default_suggestions(self, item: PARAItem) -> List[EmojiSuggestion]:
        """Get default emoji suggestions when no specific matches found.
        
        Args:
            item: PARAItem to suggest for
            
        Returns:
            List of default suggestions
        """
        defaults = []
        
        # Type-based defaults
        if item.type == ItemType.PROJECT:
            defaults.extend([
                EmojiSuggestion('🎯', 'Default for projects', 0.5, EmojiCategory.PROJECT, []),
                EmojiSuggestion('⚡', 'Active project indicator', 0.4, EmojiCategory.PROJECT, []),
                EmojiSuggestion('🚀', 'Project momentum', 0.4, EmojiCategory.PROJECT, [])
            ])
        else:  # AREA
            defaults.extend([
                EmojiSuggestion('📁', 'Default for areas', 0.5, EmojiCategory.AREA, []),
                EmojiSuggestion('🗂️', 'Organized area', 0.4, EmojiCategory.AREA, []),
                EmojiSuggestion('📋', 'Area reference', 0.4, EmojiCategory.AREA, [])
            ])
        
        # Category-based defaults
        if item.category == CategoryType.WORK:
            defaults.extend([
                EmojiSuggestion('💼', 'Work context', 0.4, EmojiCategory.WORK, []),
                EmojiSuggestion('🏢', 'Business context', 0.3, EmojiCategory.WORK, [])
            ])
        else:  # PERSONAL
            defaults.extend([
                EmojiSuggestion('🏠', 'Personal context', 0.4, EmojiCategory.PERSONAL, []),
                EmojiSuggestion('❤️', 'Personal life', 0.3, EmojiCategory.PERSONAL, [])
            ])
        
        return defaults
    
    def format_with_emoji(self, item: PARAItem, emoji: str) -> str:
        """Format item name with emoji prefix.
        
        Args:
            item: PARAItem to format
            emoji: Emoji to add as prefix
            
        Returns:
            Formatted name with emoji prefix
        """
        name = item.raw_name or item.name
        
        # Remove existing emoji if present
        if self.has_emoji_prefix(name):
            existing_emoji = self.extract_emoji_prefix(name)
            if existing_emoji:
                name = name[len(existing_emoji):].strip()
        
        return f"{emoji} {name}"
    
    def analyze_emoji_usage(self, items: List[PARAItem]) -> Dict[str, Any]:
        """Analyze emoji usage patterns across items.
        
        Args:
            items: List of PARAItem objects
            
        Returns:
            Dictionary with usage statistics
        """
        total_items = len(items)
        items_with_emoji = [item for item in items if item.has_emoji()]
        emoji_usage_rate = len(items_with_emoji) / total_items if total_items > 0 else 0
        
        # Count emoji frequencies
        emoji_counts = {}
        emoji_by_category = {cat.value: [] for cat in EmojiCategory}
        
        for item in items_with_emoji:
            emoji_prefix = self.extract_emoji_prefix(item.raw_name or item.name)
            if emoji_prefix:
                emojis = self.detect_emoji(emoji_prefix)
                for emoji in emojis:
                    emoji_counts[emoji] = emoji_counts.get(emoji, 0) + 1
                    
                    # Categorize emoji
                    category = self._classify_emoji_category(emoji, item)
                    emoji_by_category[category.value].append(emoji)
        
        # Source-specific usage
        usage_by_source = {}
        for item in items:
            source = item.source.value
            if source not in usage_by_source:
                usage_by_source[source] = {'total': 0, 'with_emoji': 0}
            
            usage_by_source[source]['total'] += 1
            if item.has_emoji():
                usage_by_source[source]['with_emoji'] += 1
        
        # Calculate rates
        for source_data in usage_by_source.values():
            if source_data['total'] > 0:
                source_data['rate'] = source_data['with_emoji'] / source_data['total']
            else:
                source_data['rate'] = 0.0
        
        return {
            'total_items': total_items,
            'items_with_emoji': len(items_with_emoji),
            'emoji_usage_rate': emoji_usage_rate,
            'most_common_emojis': dict(sorted(emoji_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            'emoji_by_category': emoji_by_category,
            'usage_by_source': usage_by_source,
            'recommendations': self._generate_emoji_recommendations(items, emoji_usage_rate)
        }
    
    def _generate_emoji_recommendations(self, items: List[PARAItem], current_rate: float) -> List[str]:
        """Generate recommendations for emoji usage improvement.
        
        Args:
            items: List of items
            current_rate: Current emoji usage rate
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if current_rate < 0.3:
            recommendations.append("Consider adding emojis to more items for better visual organization")
        
        if current_rate > 0.8:
            recommendations.append("Great emoji usage! Consider standardizing similar items")
        
        # Check for items without emojis that could benefit
        items_without_emoji = [item for item in items if not item.has_emoji()]
        if len(items_without_emoji) > 5:
            recommendations.append(f"{len(items_without_emoji)} items could benefit from emoji prefixes")
        
        # Check for consistency across sources
        sources_with_low_usage = []
        for item in items:
            source_items = [i for i in items if i.source == item.source]
            source_emoji_rate = len([i for i in source_items if i.has_emoji()]) / len(source_items)
            if source_emoji_rate < 0.5 and item.source.value not in sources_with_low_usage:
                sources_with_low_usage.append(item.source.value)
        
        if sources_with_low_usage:
            recommendations.append(f"Low emoji usage in: {', '.join(sources_with_low_usage)}")
        
        return recommendations
