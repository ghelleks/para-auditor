"""Apple Notes connector using AppleScript for PARA method folders."""
import json
import logging
import subprocess
import os
from typing import List, Dict, Optional
from pathlib import Path

from ..models.para_item import PARAItem, ItemType, ItemSource, CategoryType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AppleNotesConnector:
    """Connector for Apple Notes using AppleScript to fetch PARA method folders."""
    
    def __init__(self, script_path: Optional[str] = None):
        """Initialize Apple Notes connector.
        
        Args:
            script_path: Path to AppleScript file (optional, uses default if not provided)
        """
        if script_path:
            self.script_path = script_path
        else:
            # Default path relative to this module
            current_dir = Path(__file__).parent.parent.parent
            self.script_path = current_dir / 'scripts' / 'applescript' / 'get_notes_folders.scpt'
        
        self._validate_script_exists()
    
    def _validate_script_exists(self):
        """Validate that the AppleScript file exists."""
        if not os.path.exists(self.script_path):
            raise FileNotFoundError(f"AppleScript file not found: {self.script_path}")
    
    def get_para_folders(self) -> List[PARAItem]:
        """Fetch PARA method folders from Apple Notes.
        
        Returns:
            List of PARAItem objects representing Apple Notes folders
        """
        try:
            # Execute the AppleScript
            folder_data = self._execute_applescript()
            
            if not folder_data:
                logger.warning("No data returned from Apple Notes")
                return []
            
            # Check for errors in the response
            if 'error' in folder_data:
                logger.error(f"AppleScript error: {folder_data['error']}")
                return []
            
            para_items = []
            
            # Process Projects folders (active items)
            if 'projects' in folder_data:
                for folder_name in folder_data['projects']:
                    category_str = self._classify_folder_category(folder_name)
                    category = CategoryType.WORK if category_str == 'work' else CategoryType.PERSONAL if category_str == 'personal' else CategoryType.PERSONAL
                    
                    para_item = PARAItem(
                        name=folder_name,
                        type=ItemType.PROJECT,
                        is_active=True,
                        category=category,
                        source=ItemSource.APPLE_NOTES,
                        metadata={
                            'parent_folder': 'Projects',
                            'folder_type': 'project'
                        }
                    )
                    para_items.append(para_item)
            
            # Process Areas folders (inactive items)
            if 'areas' in folder_data:
                for folder_name in folder_data['areas']:
                    category_str = self._classify_folder_category(folder_name)
                    category = CategoryType.WORK if category_str == 'work' else CategoryType.PERSONAL if category_str == 'personal' else CategoryType.PERSONAL
                    
                    para_item = PARAItem(
                        name=folder_name,
                        type=ItemType.AREA,
                        is_active=False,
                        category=category,
                        source=ItemSource.APPLE_NOTES,
                        metadata={
                            'parent_folder': 'Areas',
                            'folder_type': 'area'
                        }
                    )
                    para_items.append(para_item)
            
            logger.info(f"Fetched {len(para_items)} folders from Apple Notes")
            return para_items
            
        except Exception as e:
            logger.error(f"Error fetching Apple Notes folders: {e}")
            raise
    
    def _execute_applescript(self) -> Optional[Dict]:
        """Execute the AppleScript and parse the JSON response.
        
        Returns:
            Dictionary containing folder data or None if failed
        """
        try:
            # Execute AppleScript using osascript
            result = subprocess.run(
                ['osascript', str(self.script_path)],
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            if result.returncode != 0:
                logger.error(f"AppleScript execution failed: {result.stderr}")
                return None
            
            # Parse JSON response
            output = result.stdout.strip()
            if not output:
                logger.warning("AppleScript returned empty output")
                return None
            
            try:
                data = json.loads(output)
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AppleScript JSON output: {e}")
                logger.debug(f"Raw output: {output}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("AppleScript execution timed out")
            return None
        except Exception as e:
            logger.error(f"Error executing AppleScript: {e}")
            return None
    
    def _classify_folder_category(self, folder_name: str) -> str:
        """Classify folder as work or personal based on name patterns.
        
        Args:
            folder_name: Name of the folder
            
        Returns:
            'work', 'personal', or 'unknown'
        """
        folder_lower = folder_name.lower()
        
        # Work-related keywords
        work_keywords = [
            'work', 'job', 'office', 'business', 'company', 'corporate',
            'client', 'project', 'meeting', 'team', 'department', 
            'professional', 'career', 'admin', 'hr', 'finance'
        ]
        
        # Personal-related keywords
        personal_keywords = [
            'personal', 'home', 'family', 'hobby', 'health', 'fitness',
            'travel', 'vacation', 'friends', 'social', 'entertainment',
            'learning', 'education', 'creative', 'art', 'music'
        ]
        
        # Check for work keywords
        for keyword in work_keywords:
            if keyword in folder_lower:
                return 'work'
        
        # Check for personal keywords
        for keyword in personal_keywords:
            if keyword in folder_lower:
                return 'personal'
        
        # Default to unknown if no patterns match
        return 'unknown'
    
    def test_connection(self) -> bool:
        """Test connection to Apple Notes.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to execute a simple AppleScript command
            result = subprocess.run(
                ['osascript', '-e', 'tell application "Notes" to get name of every folder'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                folders = result.stdout.strip().split(', ')
                logger.info(f"Apple Notes connection successful. Found {len(folders)} folders.")
                return True
            else:
                logger.error(f"Apple Notes test failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Apple Notes test timed out")
            return False
        except Exception as e:
            logger.error(f"Apple Notes connection test failed: {e}")
            return False
    
    def get_all_folders(self) -> List[str]:
        """Get all folder names from Apple Notes (for debugging/testing).
        
        Returns:
            List of folder names
        """
        try:
            result = subprocess.run(
                ['osascript', '-e', 'tell application "Notes" to get name of every folder'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                folders = result.stdout.strip().split(', ')
                return [folder.strip() for folder in folders if folder.strip()]
            else:
                logger.error(f"Failed to get all folders: {result.stderr}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting all folders: {e}")
            return []
