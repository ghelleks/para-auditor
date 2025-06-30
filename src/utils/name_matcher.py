"""Name matching utilities for fuzzy string comparison and normalization."""
import re
import logging
from typing import List, Dict, Tuple, Optional, Set
from difflib import SequenceMatcher
import unicodedata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NameMatcher:
    """Utility for fuzzy name matching and normalization."""
    
    def __init__(self, similarity_threshold: float = 0.8, emoji_aware: bool = True):
        """Initialize name matcher.
        
        Args:
            similarity_threshold: Minimum similarity score for matches (0.0-1.0)
            emoji_aware: Whether to handle emoji prefixes specially
        """
        self.similarity_threshold = similarity_threshold
        self.emoji_aware = emoji_aware
        
        # Common words to ignore in matching
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'along',
            'project', 'area', 'folder', 'task', 'item'
        }
        
        # Common abbreviations and their expansions
        self.abbreviations = {
            'dev': 'development',
            'mgmt': 'management',
            'admin': 'administration',
            'hr': 'human resources',
            'it': 'information technology',
            'qa': 'quality assurance',
            'ui': 'user interface',
            'ux': 'user experience',
            'api': 'application programming interface',
            'db': 'database',
            'ops': 'operations',
            'biz': 'business',
            'fin': 'finance',
            'mkt': 'marketing',
            'sales': 'sales',
            'eng': 'engineering'
        }
    
    def normalize_name(self, name: str) -> str:
        """Normalize a name for comparison.
        
        Args:
            name: Name to normalize
            
        Returns:
            Normalized name
        """
        if not name:
            return ""
        
        # Remove emoji if emoji_aware is enabled
        if self.emoji_aware:
            name = self._remove_emoji(name)
        
        # Convert to lowercase
        normalized = name.lower().strip()
        
        # Remove unicode accents and special characters
        normalized = unicodedata.normalize('NFKD', normalized)
        normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
        
        # Remove special characters except letters, numbers, and spaces
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Expand abbreviations
        words = normalized.split()
        expanded_words = []
        for word in words:
            if word in self.abbreviations:
                expanded_words.append(self.abbreviations[word])
            else:
                expanded_words.append(word)
        
        return ' '.join(expanded_words)
    
    def _remove_emoji(self, text: str) -> str:
        """Remove emoji characters from text.
        
        Args:
            text: Text potentially containing emojis
            
        Returns:
            Text with emojis removed
        """
        if not text:
            return ""
        
        # Unicode ranges for emojis
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002600-\U000026FF"  # miscellaneous symbols
            "\U00002700-\U000027BF"  # dingbats
            "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
            "\U0001F018-\U0001F0F5"  # mahjong tiles
            "\U0001F000-\U0001F02F"  # playing cards
            "]+", flags=re.UNICODE
        )
        
        return emoji_pattern.sub('', text).strip()
    
    def calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names.
        
        Args:
            name1: First name to compare
            name2: Second name to compare
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not name1 or not name2:
            return 0.0
        
        # Normalize names
        norm1 = self.normalize_name(name1)
        norm2 = self.normalize_name(name2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # Exact match after normalization
        if norm1 == norm2:
            return 1.0
        
        # Use multiple similarity metrics and take the maximum
        similarities = []
        
        # 1. Sequence matcher (overall similarity)
        seq_sim = SequenceMatcher(None, norm1, norm2).ratio()
        similarities.append(seq_sim)
        
        # 2. Word-based similarity
        word_sim = self._calculate_word_similarity(norm1, norm2)
        similarities.append(word_sim)
        
        # 3. Substring similarity
        substr_sim = self._calculate_substring_similarity(norm1, norm2)
        similarities.append(substr_sim)
        
        # 4. Character n-gram similarity
        ngram_sim = self._calculate_ngram_similarity(norm1, norm2, n=3)
        similarities.append(ngram_sim)
        
        # Return the maximum similarity score
        return max(similarities)
    
    def _calculate_word_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity based on word overlap.
        
        Args:
            name1: First normalized name
            name2: Second normalized name
            
        Returns:
            Word-based similarity score
        """
        words1 = set(word for word in name1.split() if word not in self.stop_words)
        words2 = set(word for word in name2.split() if word not in self.stop_words)
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _calculate_substring_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity based on longest common substring.
        
        Args:
            name1: First normalized name
            name2: Second normalized name
            
        Returns:
            Substring-based similarity score
        """
        if not name1 or not name2:
            return 0.0
        
        # Find longest common substring
        m, n = len(name1), len(name2)
        longest = 0
        
        # Create a table to store lengths of longest common substrings
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if name1[i-1] == name2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                    longest = max(longest, dp[i][j])
                else:
                    dp[i][j] = 0
        
        # Return ratio of longest common substring to average length
        avg_length = (len(name1) + len(name2)) / 2
        return longest / avg_length if avg_length > 0 else 0.0
    
    def _calculate_ngram_similarity(self, name1: str, name2: str, n: int = 3) -> float:
        """Calculate similarity based on character n-grams.
        
        Args:
            name1: First normalized name
            name2: Second normalized name
            n: Size of n-grams
            
        Returns:
            N-gram-based similarity score
        """
        if not name1 or not name2:
            return 0.0
        
        # Generate n-grams
        ngrams1 = set(name1[i:i+n] for i in range(len(name1) - n + 1))
        ngrams2 = set(name2[i:i+n] for i in range(len(name2) - n + 1))
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        # Jaccard similarity for n-grams
        intersection = len(ngrams1.intersection(ngrams2))
        union = len(ngrams1.union(ngrams2))
        
        return intersection / union if union > 0 else 0.0
    
    def is_match(self, name1: str, name2: str, threshold: Optional[float] = None) -> bool:
        """Check if two names match within the similarity threshold.
        
        Args:
            name1: First name to compare
            name2: Second name to compare
            threshold: Custom threshold (uses instance threshold if None)
            
        Returns:
            True if names match within threshold
        """
        if threshold is None:
            threshold = self.similarity_threshold
        
        similarity = self.calculate_similarity(name1, name2)
        return similarity >= threshold
    
    def find_best_matches(self, target_name: str, candidate_names: List[str], 
                         max_matches: int = 5) -> List[Tuple[str, float]]:
        """Find the best matching names from a list of candidates.
        
        Args:
            target_name: Name to find matches for
            candidate_names: List of candidate names to search
            max_matches: Maximum number of matches to return
            
        Returns:
            List of (name, similarity_score) tuples, sorted by similarity
        """
        if not target_name or not candidate_names:
            return []
        
        matches = []
        for candidate in candidate_names:
            similarity = self.calculate_similarity(target_name, candidate)
            if similarity >= self.similarity_threshold:
                matches.append((candidate, similarity))
        
        # Sort by similarity score (descending) and return top matches
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:max_matches]
    
    def group_similar_names(self, names: List[str]) -> List[List[str]]:
        """Group similar names together.
        
        Args:
            names: List of names to group
            
        Returns:
            List of groups, where each group contains similar names
        """
        if not names:
            return []
        
        groups = []
        processed = set()
        
        for name in names:
            if name in processed:
                continue
            
            # Start a new group with this name
            current_group = [name]
            processed.add(name)
            
            # Find all similar names
            for other_name in names:
                if other_name != name and other_name not in processed:
                    if self.is_match(name, other_name):
                        current_group.append(other_name)
                        processed.add(other_name)
            
            groups.append(current_group)
        
        return groups
    
    def suggest_canonical_name(self, names: List[str]) -> str:
        """Suggest a canonical name from a group of similar names.
        
        Args:
            names: List of similar names
            
        Returns:
            Suggested canonical name
        """
        if not names:
            return ""
        
        if len(names) == 1:
            return names[0]
        
        # Prefer names without abbreviations
        non_abbrev_names = []
        for name in names:
            normalized = self.normalize_name(name)
            has_abbrev = any(abbrev in normalized.split() for abbrev in self.abbreviations.keys())
            if not has_abbrev:
                non_abbrev_names.append(name)
        
        if non_abbrev_names:
            # Choose the longest non-abbreviated name
            return max(non_abbrev_names, key=len)
        
        # If all have abbreviations, choose the longest one
        return max(names, key=len)
    
    def extract_common_patterns(self, names: List[str]) -> Dict[str, int]:
        """Extract common patterns from a list of names.
        
        Args:
            names: List of names to analyze
            
        Returns:
            Dictionary of patterns and their frequencies
        """
        patterns = {}
        
        for name in names:
            normalized = self.normalize_name(name)
            words = normalized.split()
            
            # Count individual words
            for word in words:
                if len(word) > 2:  # Ignore very short words
                    patterns[word] = patterns.get(word, 0) + 1
            
            # Count bigrams
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                patterns[bigram] = patterns.get(bigram, 0) + 1
        
        return dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True))
