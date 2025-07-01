"""Todoist API connector for PARA method projects and tasks."""
import logging
from typing import List, Optional
from todoist_api_python.api import TodoistAPI

from ..models.para_item import PARAItem, ItemType, ItemSource, CategoryType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TodoistConnector:
    """Connector for Todoist API to fetch PARA method projects and tasks."""
    
    def __init__(self, api_token: str):
        """Initialize Todoist connector.
        
        Args:
            api_token: Todoist API token
        """
        self.api = TodoistAPI(api_token)
        
    def get_projects(self) -> List[PARAItem]:
        """Fetch all projects from Todoist and convert to PARAItems.
        
        Returns:
            List of PARAItem objects representing Todoist projects
        """
        try:
            projects_response = self.api.get_projects()
            para_items = []
            
            logger.debug(f"Got projects from Todoist API: {type(projects_response)}")
            if not projects_response:
                logger.warning("No projects returned from Todoist API")
                return []
            
            # Handle different response types from Todoist API
            project_list = []
            
            # If it's a ResultsPaginator, iterate through all pages
            if hasattr(projects_response, '__iter__') and not isinstance(projects_response, (list, str)):
                # This is likely a paginator - iterate through it
                try:
                    for project in projects_response:
                        project_list.append(project)
                except Exception as e:
                    logger.warning(f"Error iterating through projects paginator: {e}")
                    # Fallback: try to access as list or data attribute
                    if hasattr(projects_response, 'data'):
                        project_list = projects_response.data
                    elif isinstance(projects_response, list):
                        project_list = projects_response
                    else:
                        project_list = [projects_response]
            elif isinstance(projects_response, list):
                project_list = projects_response
            else:
                # Handle case where API returns a wrapper object
                project_list = getattr(projects_response, 'data', projects_response) if hasattr(projects_response, 'data') else [projects_response]
            
            logger.info(f"Processing {len(project_list)} projects from Todoist")
            
            for project in project_list:
                try:
                    # If the project itself is a list, it might be nested - extract projects from it
                    if isinstance(project, list):
                        logger.debug(f"Got nested list with {len(project)} projects")
                        # Process each project in the nested list
                        for nested_project in project:
                            if hasattr(nested_project, 'id') and hasattr(nested_project, 'name'):
                                # Process this individual project
                                processed_project = self._process_single_project(nested_project)
                                if processed_project:
                                    para_items.append(processed_project)
                        continue  # Skip the rest of the loop since we processed the nested list
                    
                    # Process this single project
                    processed_project = self._process_single_project(project)
                    if processed_project:
                        para_items.append(processed_project)
                    
                except Exception as e:
                    logger.error(f"Error processing project {getattr(project, 'id', 'unknown')}: {e}")
                    continue
                
            logger.info(f"Fetched {len(para_items)} projects from Todoist")
            return para_items
            
        except Exception as e:
            logger.error(f"Error fetching Todoist projects: {e}")
            raise
    
    def _process_single_project(self, project) -> Optional[PARAItem]:
        """Process a single project object and convert to PARAItem.
        
        Args:
            project: Todoist project object
            
        Returns:
            PARAItem object or None if processing failed
        """
        try:
            # Validate project object has required attributes
            if not hasattr(project, 'id'):
                logger.warning(f"Project object missing 'id' attribute: {type(project)}")
                return None
            
            if not hasattr(project, 'name'):
                logger.warning(f"Project {project.id} missing 'name' attribute")
                return None
            
            # Safely get project attributes with defaults
            project_name = getattr(project, 'name', f'Project {project.id}')
            is_favorite = getattr(project, 'is_favorite', False)
            project_color = getattr(project, 'color', None)
            project_order = getattr(project, 'order', 0)
            
            # Only process favorited projects for PARA method
            if not is_favorite:
                logger.debug(f"Skipping non-favorited project: {project_name}")
                return None
            
            # Determine category based on emoji prefix
            category = CategoryType.WORK if project_name.startswith('💼') else CategoryType.PERSONAL
            
            # Create clean name for matching (remove 💼 prefix if present)
            clean_name = project_name
            if project_name.startswith('💼'):
                clean_name = project_name[1:].strip()  # Remove 💼 and any following whitespace
            
            
            para_item = PARAItem(
                name=clean_name,  # Use clean name for matching
                raw_name=project_name,  # Store original name with emoji
                type=ItemType.PROJECT if is_favorite else ItemType.AREA,
                is_active=is_favorite,
                category=category,
                source=ItemSource.TODOIST,
                metadata={
                    'project_id': project.id,
                    'color': project_color,
                    'order': project_order
                }
            )
            return para_item
            
        except Exception as e:
            logger.error(f"Error processing project {getattr(project, 'id', 'unknown')}: {e}")
            return None
    
    
    
    
    def test_connection(self) -> bool:
        """Test connection to Todoist API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            projects_response = self.api.get_projects()
            
            # Count projects by iterating through response
            project_count = 0
            if hasattr(projects_response, '__iter__') and not isinstance(projects_response, (list, str)):
                # This is likely a paginator - iterate through it
                try:
                    for _ in projects_response:
                        project_count += 1
                except:
                    # Fallback counting method
                    if hasattr(projects_response, 'data'):
                        project_count = len(projects_response.data) if isinstance(projects_response.data, list) else 1
                    elif isinstance(projects_response, list):
                        project_count = len(projects_response)
                    else:
                        project_count = 1 if projects_response else 0
            elif isinstance(projects_response, list):
                project_count = len(projects_response)
            else:
                project_count = 1 if projects_response else 0
            
            logger.info(f"Todoist connection successful. Found {project_count} projects.")
            return True
        except Exception as e:
            logger.error(f"Todoist connection failed: {e}")
            return False
