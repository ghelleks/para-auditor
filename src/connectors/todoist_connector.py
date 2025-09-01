"""Todoist API connector for PARA method projects and tasks."""
import logging
from typing import List, Optional
from todoist_api_python.api import TodoistAPI

from ..models.para_item import PARAItem, ItemType, ItemSource, CategoryType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TodoistConnector:
    """Connector for Todoist API to fetch projects and tasks."""
    
    def __init__(self, api_token: str, next_action_label: str = "next"):
        """Initialize Todoist connector.
        
        Args:
            api_token: Todoist API token
            next_action_label: Label name to check for next actions (without '@' prefix)
        """
        self.api_token = api_token
        self.api = TodoistAPI(api_token)
        self.next_action_label = self._normalize_label_name(next_action_label)
        
        # Cache for next action tasks to avoid repeated API calls
        self._next_action_tasks_cache = None
        self._cache_populated = False

    def get_projects(self) -> List[PARAItem]:
        """Fetch all projects from Todoist and convert to PARAItems.
        
        Returns:
            List of PARAItem objects representing Todoist projects
        """
        try:
            # Reset cache for each get_projects call
            self._next_action_tasks_cache = None
            self._cache_populated = False
            
            # Pre-populate the next action tasks cache to avoid repeated API calls
            self._populate_next_action_cache()
            
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

    def _populate_next_action_cache(self):
        """Pre-populate the cache with next action tasks to avoid repeated API calls."""
        if self._cache_populated:
            return
            
        try:
            logger.debug(f"Pre-populating cache with @{self.next_action_label} tasks")
            self._next_action_tasks_cache = self.get_tasks_with_label(self.next_action_label)
            self._cache_populated = True
            logger.debug(f"Cached {len(self._next_action_tasks_cache)} @{self.next_action_label} tasks")
        except Exception as e:
            logger.error(f"Error populating next action cache: {e}")
            self._next_action_tasks_cache = []
            self._cache_populated = True

    def _get_cached_next_action_tasks(self) -> List:
        """Get cached next action tasks, populating cache if necessary."""
        if not self._cache_populated:
            self._populate_next_action_cache()
        return self._next_action_tasks_cache or []
    
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
            
            # Process both favorited projects (Projects) and non-favorited projects (Areas) for PARA method
            # Note: We now include areas to check for next actions
            
            # Determine category based on emoji prefix
            category = CategoryType.WORK if project_name.startswith('💼') else CategoryType.PERSONAL
            
            # Create clean name for matching (remove 💼 prefix if present)
            clean_name = project_name
            if project_name.startswith('💼'):
                clean_name = project_name[1:].strip()  # Remove 💼 and any following whitespace
            
            
            # Check for next action in both projects and areas
            has_next_action = False
            next_action_count = 0
            next_action_tasks = []
            
            # Check for next actions in all projects/areas
            has_next_action = self.check_project_has_next_action(project.id)
            if has_next_action:
                next_action_task_objects = self.get_next_action_tasks_for_project(project.id)
                next_action_count = len(next_action_task_objects)
                next_action_tasks = [getattr(task, 'content', 'Untitled Task') for task in next_action_task_objects]
                logger.debug(f"{'Project' if is_favorite else 'Area'} '{project_name}' has {next_action_count} @{self.next_action_label} tasks")
            else:
                logger.debug(f"{'Project' if is_favorite else 'Area'} '{project_name}' has no @{self.next_action_label} tasks")
            
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
                    'order': project_order,
                    'has_next_action': has_next_action,
                    'next_action_count': next_action_count,
                    'next_action_tasks': next_action_tasks,
                    'next_action_label': self.next_action_label
                }
            )
            return para_item
            
        except Exception as e:
            logger.error(f"Error processing project {getattr(project, 'id', 'unknown')}: {e}")
            return None
    
    def _normalize_label_name(self, label_name: str) -> str:
        """Normalize label name by removing '@' prefix if present.
        
        Args:
            label_name: Raw label name (may include '@' prefix)
            
        Returns:
            Normalized label name without '@' prefix
        """
        return label_name.lstrip('@')
    
    def get_tasks_for_project(self, project_id: str) -> List:
        """Fetch all tasks for a specific project from Todoist.
        
        Args:
            project_id: Todoist project ID
            
        Returns:
            List of Task objects for the project
        """
        try:
            # Try with project_id parameter
            tasks = None
            try:
                tasks = self.api.get_tasks(project_id=project_id)
            except TypeError as e:
                logger.debug(f"get_tasks with project_id failed: {e}, trying alternative approaches")
                # If project_id parameter doesn't work, get all tasks and filter locally
                try:
                    all_tasks = self.api.get_tasks()
                    # Filter tasks that belong to the project
                    task_list = []
                    if hasattr(all_tasks, '__iter__') and not isinstance(all_tasks, (list, str)):
                        for task in all_tasks:
                            if hasattr(task, 'project_id') and str(task.project_id) == str(project_id):
                                task_list.append(task)
                    elif isinstance(all_tasks, list):
                        for task in all_tasks:
                            if hasattr(task, 'project_id') and str(task.project_id) == str(project_id):
                                task_list.append(task)
                    return task_list
                except Exception as e2:
                    logger.error(f"Failed to get all tasks: {e2}")
                    return []
            
            if tasks is None:
                return []
            
            # Handle different response types - be more explicit about list handling
            if isinstance(tasks, list):
                logger.debug(f"Tasks is a list with {len(tasks)} items")
                return tasks
            elif hasattr(tasks, '__iter__') and not isinstance(tasks, str):
                # This is likely a paginator - convert to list
                try:
                    task_list = list(tasks)
                    logger.debug(f"Converted paginator to list with {len(task_list)} tasks")
                    return task_list
                except Exception as e:
                    logger.warning(f"Error converting paginator to list: {e}")
                    return []
            elif hasattr(tasks, 'data'):
                data = tasks.data
                if isinstance(data, list):
                    logger.debug(f"Found data attribute with {len(data)} tasks")
                    return data
                else:
                    logger.debug(f"Data attribute is not a list: {type(data)}")
                    return [data] if data else []
            else:
                logger.debug(f"Unknown tasks type: {type(tasks)}")
                return [tasks] if tasks else []
            
        except Exception as e:
            logger.error(f"Error fetching tasks for project {project_id}: {e}")
            return []
    
    def get_tasks_with_label(self, label_name: str) -> List:
        """Fetch all tasks with a specific label.
        
        Args:
            label_name: Label name without '@' prefix (e.g., 'next', 'waiting')
            
        Returns:
            List of Task objects with the specified label
        """
        try:
            normalized_label = self._normalize_label_name(label_name)
            logger.debug(f"Fetching tasks with label: @{normalized_label}")
            
            # Try with filter parameter (REST API v2 style)
            try:
                tasks = self.api.get_tasks(filter=f"@{normalized_label}")
                logger.debug(f"Filter API call returned: {type(tasks)}")
            except TypeError as e:
                logger.debug(f"get_tasks with filter failed: {e}, trying alternative approaches")
                # If filter parameter doesn't work, try getting all tasks and filtering locally
                try:
                    all_tasks = self.api.get_tasks()
                    logger.debug(f"Got all tasks: {type(all_tasks)}")
                    
                    # Flatten the paginated task list and filter by label
                    task_list = []
                    if isinstance(all_tasks, list):
                        # All tasks is already a list
                        for task in all_tasks:
                            if hasattr(task, 'labels') and normalized_label in task.labels:
                                task_list.append(task)
                    else:
                        # Handle paginated response - flatten the pages
                        for page in all_tasks:
                            if isinstance(page, list):
                                # Each page is a list of tasks
                                for task in page:
                                    if hasattr(task, 'labels') and normalized_label in task.labels:
                                        task_list.append(task)
                            else:
                                # Single task
                                if hasattr(page, 'labels') and normalized_label in page.labels:
                                    task_list.append(page)
                    
                    logger.debug(f"Filtered {len(task_list)} tasks with @{normalized_label} label")
                    return task_list
                except Exception as e2:
                    logger.error(f"Failed to get all tasks: {e2}")
                    return []
            
            if tasks is None:
                logger.debug("Tasks is None, returning empty list")
                return []
            
            # Handle different response types - be more explicit about list handling
            if isinstance(tasks, list):
                logger.debug(f"Tasks is a list with {len(tasks)} items")
                return tasks
            elif hasattr(tasks, '__iter__') and not isinstance(tasks, str):
                # This is likely a paginator - convert to list
                try:
                    task_list = list(tasks)
                    logger.debug(f"Converted paginator to list with {len(task_list)} tasks")
                    return task_list
                except Exception as e:
                    logger.warning(f"Error converting paginator to list: {e}")
                    return []
            elif hasattr(tasks, 'data'):
                data = tasks.data
                if isinstance(data, list):
                    logger.debug(f"Found data attribute with {len(data)} tasks")
                    return data
                else:
                    logger.debug(f"Data attribute is not a list: {type(data)}")
                    return [data] if data else []
            else:
                logger.debug(f"Unknown tasks type: {type(tasks)}")
                return [tasks] if tasks else []
            
        except Exception as e:
            logger.error(f"Error fetching tasks with label '@{normalized_label}': {e}")
            return []
    
    def check_project_has_next_action(self, project_id: str, next_action_label: str = None) -> bool:
        """Check if a project has at least one task with specified label.
        
        Args:
            project_id: Todoist project ID
            next_action_label: Label name to check for (without '@' prefix). If None, uses instance default.
            
        Returns:
            True if project has at least one task with the specified label
        """
        if next_action_label is None:
            next_action_label = self.next_action_label
        else:
            next_action_label = self._normalize_label_name(next_action_label)
        
        try:
            # Use cached tasks if available and label matches our instance label
            if next_action_label == self.next_action_label:
                tasks_with_label = self._get_cached_next_action_tasks()
            else:
                # If different label requested, fetch it directly
                tasks_with_label = self.get_tasks_with_label(next_action_label)
            
            # Check if any of these tasks belong to the specified project
            for task in tasks_with_label:
                if hasattr(task, 'project_id') and task.project_id == project_id:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking next action for project {project_id}: {e}")
            return False
    
    def get_next_action_tasks_for_project(self, project_id: str, next_action_label: str = None) -> List:
        """Get all tasks with next action label for a specific project.
        
        Args:
            project_id: Todoist project ID
            next_action_label: Label name to check for (without '@' prefix). If None, uses instance default.
            
        Returns:
            List of Task objects with next action label in the specified project
        """
        if next_action_label is None:
            next_action_label = self.next_action_label
        else:
            next_action_label = self._normalize_label_name(next_action_label)
        
        try:
            # Use cached tasks if available and label matches our instance label
            if next_action_label == self.next_action_label:
                tasks_with_label = self._get_cached_next_action_tasks()
            else:
                # If different label requested, fetch it directly
                tasks_with_label = self.get_tasks_with_label(next_action_label)
            
            # Filter tasks that belong to the specified project
            project_tasks = []
            for task in tasks_with_label:
                if hasattr(task, 'project_id') and task.project_id == project_id:
                    project_tasks.append(task)
            
            return project_tasks
            
        except Exception as e:
            logger.error(f"Error getting next action tasks for project {project_id}: {e}")
            return []
    
    def validate_label_exists(self, label_name: str) -> bool:
        """Check if a label exists in Todoist.
        
        Args:
            label_name: Label name to validate
            
        Returns:
            True if label exists, False otherwise
        """
        try:
            normalized_label = self._normalize_label_name(label_name)
            # Try to fetch tasks with this label - if it doesn't exist, no tasks will be returned
            # This is a safe way to check without causing errors
            self.get_tasks_with_label(normalized_label)
            return True
        except Exception as e:
            logger.warning(f"Label '@{normalized_label}' validation failed: {e}")
            return False
    
    def get_areas_missing_next_actions(self) -> List:
        """Get all areas (non-favorited projects) that don't have next action tasks.
        
        Returns:
            List of PARAItem objects representing areas without next actions
        """
        try:
            all_items = self.get_projects()  # This now includes both projects and areas
            areas_without_next = []
            
            for item in all_items:
                # Only check areas (non-favorited items)
                if item.type == ItemType.AREA:
                    has_next = item.metadata.get('has_next_action', False)
                    if not has_next:
                        areas_without_next.append(item)
                        logger.debug(f"Area '{item.raw_name}' missing @{self.next_action_label} task")
            
            logger.info(f"Found {len(areas_without_next)} areas missing @{self.next_action_label} tasks")
            return areas_without_next
            
        except Exception as e:
            logger.error(f"Error finding areas missing next actions: {e}")
            return []

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
