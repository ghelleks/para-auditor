"""Todoist API connector for PARA method projects and tasks."""
import re
import logging
from typing import List, Dict, Optional, Set
from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Project, Task

from ..models.para_item import PARAItem, ItemType, ItemSource, CategoryType
from ..utils.url_parser import URLParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TodoistConnector:
    """Connector for Todoist API to fetch PARA method projects and tasks."""
    
    def __init__(self, api_token: str, work_domains: List[str] = None, personal_domains: List[str] = None):
        """Initialize Todoist connector.
        
        Args:
            api_token: Todoist API token
            work_domains: List of work email domains for classification
            personal_domains: List of personal email domains for classification
        """
        self.api = TodoistAPI(api_token)
        self.work_domains = work_domains or []
        self.personal_domains = personal_domains or []
        self.url_parser = URLParser(work_domains, personal_domains)
        
    def get_projects(self) -> List[PARAItem]:
        """Fetch all projects from Todoist and convert to PARAItems.
        
        Returns:
            List of PARAItem objects representing Todoist projects
        """
        try:
            projects = self.api.get_projects()
            para_items = []
            
            for project in projects:
                # Get tasks for this project to extract Google Drive links
                tasks = self._get_project_tasks(project.id)
                gdrive_links = self._extract_gdrive_links(tasks)
                
                # Determine category based on Google Drive links
                category_str = self._classify_project_category(gdrive_links)
                category = CategoryType.WORK if category_str == 'work' else CategoryType.PERSONAL if category_str == 'personal' else CategoryType.PERSONAL
                
                para_item = PARAItem(
                    name=project.name,
                    type=ItemType.PROJECT if project.is_favorite else ItemType.AREA,
                    is_active=project.is_favorite,
                    category=category,
                    source=ItemSource.TODOIST,
                    metadata={
                        'project_id': project.id,
                        'gdrive_links': gdrive_links,
                        'color': project.color,
                        'order': project.order,
                        'task_count': len(tasks)
                    }
                )
                para_items.append(para_item)
                
            logger.info(f"Fetched {len(para_items)} projects from Todoist")
            return para_items
            
        except Exception as e:
            logger.error(f"Error fetching Todoist projects: {e}")
            raise
    
    def _get_project_tasks(self, project_id: str) -> List[Task]:
        """Get all tasks for a specific project.
        
        Args:
            project_id: Todoist project ID
            
        Returns:
            List of Task objects
        """
        try:
            tasks = self.api.get_tasks(project_id=project_id)
            return tasks
        except Exception as e:
            logger.warning(f"Error fetching tasks for project {project_id}: {e}")
            return []
    
    def _extract_gdrive_links(self, tasks: List[Task]) -> List[str]:
        """Extract Google Drive links from task content.
        
        Args:
            tasks: List of Task objects
            
        Returns:
            List of Google Drive URLs found in task content
        """
        gdrive_links = []
        
        # Regex patterns for various Google Drive URL formats
        patterns = [
            r'https://drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)',
            r'https://drive\.google\.com/drive/u/\d+/folders/([a-zA-Z0-9_-]+)',
            r'https://drive\.google\.com/drive/u/\d+/folders/([a-zA-Z0-9_-]+)\?[^\s]*',
            r'https://drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)\?[^\s]*',
            r'https://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)',
            r'https://docs\.google\.com/.*?/d/([a-zA-Z0-9_-]+)',
        ]
        
        combined_pattern = '|'.join(f'({pattern})' for pattern in patterns)
        
        for task in tasks:
            if task.content:
                matches = re.findall(combined_pattern, task.content, re.IGNORECASE)
                for match_groups in matches:
                    # Extract the actual URL from the match groups
                    for group in match_groups:
                        if group and group.startswith('https://'):
                            gdrive_links.append(group)
                            break
        
        # Remove duplicates while preserving order
        seen = set()
        unique_links = []
        for link in gdrive_links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        return unique_links
    
    def _classify_project_category(self, gdrive_links: List[str]) -> str:
        """Classify project as work or personal based on Google Drive links.
        
        Args:
            gdrive_links: List of Google Drive URLs
            
        Returns:
            'work', 'personal', or 'unknown'
        """
        if not gdrive_links:
            return 'unknown'
        
        work_count = 0
        personal_count = 0
        
        for link in gdrive_links:
            try:
                parsed = self.url_parser.parse_drive_url(link)
                if parsed and parsed.get('account_type'):
                    if parsed['account_type'] == 'work':
                        work_count += 1
                    elif parsed['account_type'] == 'personal':
                        personal_count += 1
            except Exception as e:
                logger.warning(f"Error parsing Google Drive URL {link}: {e}")
                continue
        
        # Determine category based on majority of links
        if work_count > personal_count:
            return 'work'
        elif personal_count > work_count:
            return 'personal'
        else:
            return 'unknown'
    
    def test_connection(self) -> bool:
        """Test connection to Todoist API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            projects = self.api.get_projects()
            logger.info(f"Todoist connection successful. Found {len(projects)} projects.")
            return True
        except Exception as e:
            logger.error(f"Todoist connection failed: {e}")
            return False
