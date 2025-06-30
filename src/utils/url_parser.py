"""URL parsing utilities for Google Drive links and account classification."""
import re
import logging
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class URLParser:
    """Parser for Google Drive URLs and account classification."""
    
    def __init__(self, work_domains: List[str] = None, personal_domains: List[str] = None):
        """Initialize URL parser.
        
        Args:
            work_domains: List of work email domains for classification
            personal_domains: List of personal email domains for classification
        """
        self.work_domains = work_domains or []
        self.personal_domains = personal_domains or []
        
        # Regex patterns for various Google Drive URL formats
        self.gdrive_patterns = [
            # Standard folder URLs
            r'https://drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)',
            # User-specific folder URLs
            r'https://drive\.google\.com/drive/u/\d+/folders/([a-zA-Z0-9_-]+)',
            # Folder URLs with parameters
            r'https://drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)\?[^\s]*',
            r'https://drive\.google\.com/drive/u/\d+/folders/([a-zA-Z0-9_-]+)\?[^\s]*',
            # Open URLs
            r'https://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)',
            # Document URLs (for folder IDs in sharing URLs)
            r'https://docs\.google\.com/.*?/d/([a-zA-Z0-9_-]+)',
            # File URLs
            r'https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',
            # Alternative file URLs
            r'https://drive\.google\.com/uc\?id=([a-zA-Z0-9_-]+)',
        ]
        
        # Compiled regex patterns for better performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.gdrive_patterns]
    
    def parse_drive_url(self, url: str) -> Optional[Dict[str, Union[str, bool]]]:
        """Parse a Google Drive URL and extract metadata.
        
        Args:
            url: Google Drive URL to parse
            
        Returns:
            Dictionary with parsed URL information or None if invalid
        """
        if not url or not isinstance(url, str):
            return None
        
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            return None
        
        try:
            parsed_url = urlparse(url)
            
            # Check if it's a Google Drive URL
            if not self._is_google_drive_url(parsed_url.netloc):
                return None
            
            # Extract folder/file ID
            file_id = self._extract_id_from_url(url)
            if not file_id:
                return None
            
            # Determine account type
            account_type = self._classify_account_type(url, parsed_url)
            
            # Determine resource type (folder, file, etc.)
            resource_type = self._determine_resource_type(url, parsed_url)
            
            return {
                'url': url,
                'file_id': file_id,
                'account_type': account_type,
                'resource_type': resource_type,
                'domain': parsed_url.netloc,
                'is_shared': self._is_shared_url(url),
                'user_index': self._extract_user_index(url)
            }
            
        except Exception as e:
            logger.warning(f"Error parsing URL {url}: {e}")
            return None
    
    def _is_google_drive_url(self, netloc: str) -> bool:
        """Check if URL is from Google Drive domain.
        
        Args:
            netloc: Network location from parsed URL
            
        Returns:
            True if it's a Google Drive URL
        """
        google_domains = [
            'drive.google.com',
            'docs.google.com',
            'sheets.google.com',
            'slides.google.com'
        ]
        
        return any(domain in netloc.lower() for domain in google_domains)
    
    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Extract file/folder ID from Google Drive URL.
        
        Args:
            url: Google Drive URL
            
        Returns:
            File/folder ID or None if not found
        """
        for pattern in self.compiled_patterns:
            match = pattern.search(url)
            if match:
                return match.group(1)
        
        # Try to extract from query parameters
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            if 'id' in query_params:
                return query_params['id'][0]
        except Exception:
            pass
        
        return None
    
    def _classify_account_type(self, url: str, parsed_url) -> str:
        """Classify URL as work or personal account.
        
        Args:
            url: Original URL
            parsed_url: Parsed URL object
            
        Returns:
            'work', 'personal', or 'unknown'
        """
        # Method 1: Check user index in URL (u/0, u/1, etc.)
        user_index = self._extract_user_index(url)
        if user_index is not None:
            # Typically u/0 is personal, u/1 is work (but this varies)
            # We'll use domain classification as primary method
            pass
        
        # Method 2: Check for domain hints in URL parameters
        try:
            query_params = parse_qs(parsed_url.query)
            if 'authuser' in query_params:
                auth_user = query_params['authuser'][0]
                # Check if auth_user contains domain information
                for domain in self.work_domains:
                    if domain in auth_user:
                        return 'work'
                for domain in self.personal_domains:
                    if domain in auth_user:
                        return 'personal'
        except Exception:
            pass
        
        # Method 3: Heuristic based on user index
        if user_index is not None:
            # Common pattern: u/0 = primary (often personal), u/1+ = secondary (often work)
            # But this is not reliable, so we return unknown
            pass
        
        return 'unknown'
    
    def _extract_user_index(self, url: str) -> Optional[int]:
        """Extract user index from Google Drive URL (e.g., u/1).
        
        Args:
            url: Google Drive URL
            
        Returns:
            User index number or None if not found
        """
        match = re.search(r'/u/(\d+)/', url)
        if match:
            return int(match.group(1))
        return None
    
    def _determine_resource_type(self, url: str, parsed_url) -> str:
        """Determine if URL points to folder, file, or other resource.
        
        Args:
            url: Original URL
            parsed_url: Parsed URL object
            
        Returns:
            'folder', 'file', 'document', or 'unknown'
        """
        url_lower = url.lower()
        
        if '/folders/' in url_lower:
            return 'folder'
        elif '/file/' in url_lower or '/uc?id=' in url_lower:
            return 'file'
        elif 'docs.google.com' in parsed_url.netloc:
            if '/document/' in url_lower:
                return 'document'
            elif '/spreadsheets/' in url_lower:
                return 'spreadsheet'
            elif '/presentation/' in url_lower:
                return 'presentation'
            else:
                return 'document'
        elif 'open?id=' in url_lower:
            # Could be either file or folder, need additional context
            return 'unknown'
        else:
            return 'unknown'
    
    def _is_shared_url(self, url: str) -> bool:
        """Check if URL appears to be a sharing URL.
        
        Args:
            url: Google Drive URL
            
        Returns:
            True if it appears to be a sharing URL
        """
        sharing_indicators = [
            'usp=sharing',
            'usp=drive_link',
            '/edit?',
            '/view?',
            'open?id='
        ]
        
        return any(indicator in url for indicator in sharing_indicators)
    
    def extract_all_drive_urls(self, text: str) -> List[str]:
        """Extract all Google Drive URLs from a text string.
        
        Args:
            text: Text containing potential Google Drive URLs
            
        Returns:
            List of Google Drive URLs found in the text
        """
        if not text:
            return []
        
        urls = []
        
        # Use regex to find all potential URLs
        for pattern in self.compiled_patterns:
            matches = pattern.findall(text)
            for match in matches:
                # Reconstruct the full URL
                if isinstance(match, tuple):
                    # Handle grouped matches
                    for group in match:
                        if group and group.startswith('https://'):
                            urls.append(group)
                            break
                elif match.startswith('https://'):
                    urls.append(match)
        
        # Also look for complete URLs in text
        url_pattern = re.compile(
            r'https://(?:drive|docs|sheets|slides)\.google\.com/[^\s<>"]+',
            re.IGNORECASE
        )
        
        complete_urls = url_pattern.findall(text)
        urls.extend(complete_urls)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls
    
    def normalize_drive_url(self, url: str) -> Optional[str]:
        """Normalize a Google Drive URL to a standard format.
        
        Args:
            url: Google Drive URL to normalize
            
        Returns:
            Normalized URL or None if invalid
        """
        parsed = self.parse_drive_url(url)
        if not parsed:
            return None
        
        file_id = parsed['file_id']
        resource_type = parsed['resource_type']
        
        # Create normalized URL based on resource type
        if resource_type == 'folder':
            return f'https://drive.google.com/drive/folders/{file_id}'
        elif resource_type in ['file', 'unknown']:
            return f'https://drive.google.com/file/d/{file_id}'
        elif resource_type == 'document':
            return f'https://docs.google.com/document/d/{file_id}'
        elif resource_type == 'spreadsheet':
            return f'https://docs.google.com/spreadsheets/d/{file_id}'
        elif resource_type == 'presentation':
            return f'https://docs.google.com/presentation/d/{file_id}'
        else:
            # Default to drive URL
            return f'https://drive.google.com/open?id={file_id}'
    
    def validate_drive_url(self, url: str) -> bool:
        """Validate if a URL is a valid Google Drive URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid Google Drive URL
        """
        return self.parse_drive_url(url) is not None
