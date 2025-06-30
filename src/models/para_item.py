"""Data models for PARA items and related structures."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
import re


class ItemType(Enum):
    """Enum for PARA item types."""
    PROJECT = "Project"
    AREA = "Area"


class ItemSource(Enum):
    """Enum for source types where items are found."""
    TODOIST = "todoist"
    APPLE_NOTES = "apple_notes"
    GDRIVE_PERSONAL = "gdrive_personal"
    GDRIVE_WORK = "gdrive_work"


class CategoryType(Enum):
    """Enum for item categories."""
    WORK = "work"
    PERSONAL = "personal"


@dataclass
class PARAItem:
    """Represents a PARA method item (Project or Area) from any source."""
    
    name: str
    type: ItemType
    is_active: bool
    category: CategoryType
    source: ItemSource
    raw_name: Optional[str] = None  # Original name before normalization
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate and normalize data after initialization."""
        # Store original name if not provided
        if self.raw_name is None:
            self.raw_name = self.name
            
        # Normalize the name
        self.name = self.normalize_name(self.name)
        
        # Initialize metadata if not provided
        if self.metadata is None:
            self.metadata = {}
            
        # Validate required fields
        self._validate()
    
    def _validate(self):
        """Validate the PARAItem data."""
        if not self.name or not self.name.strip():
            raise ValueError("Item name cannot be empty")
            
        if not isinstance(self.type, ItemType):
            raise ValueError("type must be an ItemType enum")
            
        if not isinstance(self.source, ItemSource):
            raise ValueError("source must be a ItemSource enum")
            
        if not isinstance(self.category, CategoryType):
            raise ValueError("category must be a CategoryType enum")
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize item name for comparison."""
        if not name:
            return ""
            
        # Remove leading/trailing whitespace
        normalized = name.strip()
        
        # Convert to lowercase for comparison
        normalized = normalized.lower()
        
        # Remove special characters except letters, numbers, spaces, and emojis
        # Keep emojis by preserving Unicode characters
        normalized = re.sub(r'[^\w\s\U00010000-\U0010ffff]', '', normalized, flags=re.UNICODE)
        
        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.strip()
    
    def has_emoji(self) -> bool:
        """Check if the item name starts with an emoji."""
        if not self.raw_name:
            return False
            
        # Check if first character is an emoji
        first_char = self.raw_name[0] if self.raw_name else ""
        
        # Unicode ranges for emojis
        emoji_ranges = [
            (0x1F600, 0x1F64F),  # Emoticons
            (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
            (0x1F680, 0x1F6FF),  # Transport and Map
            (0x1F1E0, 0x1F1FF),  # Regional indicators
            (0x2600, 0x26FF),    # Misc symbols
            (0x2700, 0x27BF),    # Dingbats
            (0xFE00, 0xFE0F),    # Variation Selectors
            (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
        ]
        
        char_code = ord(first_char)
        return any(start <= char_code <= end for start, end in emoji_ranges)
    
    def get_name_without_emoji(self) -> str:
        """Get the item name without emoji prefix."""
        if not self.raw_name:
            return ""
            
        # Remove emoji from the beginning and strip whitespace
        result = self.raw_name
        while result and len(result) > 0:
            first_char = result[0]
            char_code = ord(first_char)
            
            # Check if first character is an emoji
            emoji_ranges = [
                (0x1F600, 0x1F64F),  # Emoticons
                (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
                (0x1F680, 0x1F6FF),  # Transport and Map
                (0x1F1E0, 0x1F1FF),  # Regional indicators
                (0x2600, 0x26FF),    # Misc symbols
                (0x2700, 0x27BF),    # Dingbats
                (0xFE00, 0xFE0F),    # Variation Selectors
                (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
            ]
            
            is_emoji = any(start <= char_code <= end for start, end in emoji_ranges)
            if not is_emoji:
                break
                
            result = result[1:].strip()
            
        return result
    
    def matches_name(self, other_name: str, threshold: float = 0.8) -> bool:
        """Check if this item's name matches another name within threshold."""
        if not other_name:
            return False
            
        normalized_other = self.normalize_name(other_name)
        return self._calculate_similarity(self.name, normalized_other) >= threshold
    
    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names using simple string matching."""
        if not name1 or not name2:
            return 0.0
            
        if name1 == name2:
            return 1.0
            
        # Simple substring matching
        shorter = name1 if len(name1) < len(name2) else name2
        longer = name2 if len(name1) < len(name2) else name1
        
        if shorter in longer:
            return len(shorter) / len(longer)
            
        # Character-based similarity
        matches = sum(1 for c1, c2 in zip(name1, name2) if c1 == c2)
        max_length = max(len(name1), len(name2))
        
        return matches / max_length if max_length > 0 else 0.0
    
    def is_consistent_with(self, other: 'PARAItem') -> bool:
        """Check if this item is consistent with another item."""
        if not self.matches_name(other.raw_name or other.name):
            return False
            
        # Check type consistency
        if self.type != other.type:
            return False
            
        # Check active status consistency
        if self.is_active != other.is_active:
            return False
            
        # Check category consistency (if both have categories)
        if self.category != other.category:
            return False
            
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert PARAItem to dictionary."""
        return {
            "name": self.name,
            "raw_name": self.raw_name,
            "type": self.type.value,
            "is_active": self.is_active,
            "category": self.category.value,
            "source": self.source.value,
            "has_emoji": self.has_emoji(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PARAItem':
        """Create PARAItem from dictionary."""
        return cls(
            name=data["name"],
            type=ItemType(data["type"]),
            is_active=data["is_active"],
            category=CategoryType(data["category"]),
            source=ItemSource(data["source"]),
            raw_name=data.get("raw_name"),
            metadata=data.get("metadata")
        )
    
    def __str__(self) -> str:
        """String representation of PARAItem."""
        emoji_status = "📱" if self.has_emoji() else "❌"
        active_status = "✅" if self.is_active else "⭕"
        
        return (f"{emoji_status} {active_status} {self.raw_name or self.name} "
                f"({self.type.value}, {self.category.value}, {self.source.value})")
    
    def __repr__(self) -> str:
        """Detailed representation of PARAItem."""
        return (f"PARAItem(name='{self.name}', raw_name='{self.raw_name}', "
                f"type={self.type}, active={self.is_active}, "
                f"category={self.category}, source={self.source})")
    
    def __eq__(self, other) -> bool:
        """Check equality based on normalized name and source."""
        if not isinstance(other, PARAItem):
            return False
            
        return (self.name == other.name and 
                self.source == other.source and
                self.category == other.category)
    
    def __hash__(self) -> int:
        """Hash based on normalized name, source, and category."""
        return hash((self.name, self.source, self.category))