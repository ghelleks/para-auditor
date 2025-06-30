"""Todoist API authentication and connection handling."""

import logging
import requests
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


class TodoistAuthError(Exception):
    """Custom exception for Todoist authentication errors."""
    pass


class TodoistAuthenticator:
    """Handles Todoist API authentication and connection testing."""
    
    BASE_URL = "https://api.todoist.com/rest/v2"
    
    def __init__(self, config_manager):
        """Initialize with configuration manager."""
        self.config_manager = config_manager
        self.api_token = config_manager.todoist_token
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'PARA-Auditor/0.1.0'
        })
        
        return session
    
    def validate_token(self) -> bool:
        """
        Validate the Todoist API token.
        
        Returns:
            True if token is valid, False otherwise
            
        Raises:
            TodoistAuthError: If validation fails due to network or API issues
        """
        if not self.api_token or self.api_token == "your_todoist_token_here":
            logger.error("Todoist API token is not configured")
            return False
            
        try:
            logger.info("Validating Todoist API token")
            
            # Test the token by making a simple API call
            response = self.session.get(f"{self.BASE_URL}/projects", timeout=10)
            
            if response.status_code == 200:
                logger.info("Todoist API token is valid")
                return True
            elif response.status_code == 401:
                logger.error("Todoist API token is invalid (401 Unauthorized)")
                return False
            elif response.status_code == 403:
                logger.error("Todoist API token access is forbidden (403 Forbidden)")
                return False
            else:
                logger.error(f"Unexpected response from Todoist API: {response.status_code}")
                raise TodoistAuthError(f"API validation failed with status {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.error("Todoist API request timed out")
            raise TodoistAuthError("API request timed out")
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to Todoist API")
            raise TodoistAuthError("Failed to connect to Todoist API")
        except requests.exceptions.RequestException as e:
            logger.error(f"Todoist API request failed: {e}")
            raise TodoistAuthError(f"API request failed: {e}")
    
    def test_connection(self) -> bool:
        """
        Test connection to Todoist API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            return self.validate_token()
        except TodoistAuthError:
            return False
    
    def get_user_info(self) -> Dict[str, Any]:
        """
        Get information about the authenticated user.
        
        Returns:
            Dictionary containing user information
            
        Raises:
            TodoistAuthError: If the request fails
        """
        if not self.validate_token():
            raise TodoistAuthError("Invalid API token")
            
        try:
            logger.info("Fetching Todoist user information")
            
            # Get user info using the labels endpoint (simpler than user endpoint)
            response = self.session.get(f"{self.BASE_URL}/labels", timeout=10)
            
            if response.status_code == 200:
                # For privacy, we'll get basic info from the projects endpoint
                projects_response = self.session.get(f"{self.BASE_URL}/projects", timeout=10)
                
                if projects_response.status_code == 200:
                    projects = projects_response.json()
                    
                    return {
                        'authenticated': True,
                        'project_count': len(projects),
                        'api_endpoint': self.BASE_URL,
                        'token_status': 'valid'
                    }
                else:
                    raise TodoistAuthError(f"Failed to fetch user data: {projects_response.status_code}")
            else:
                raise TodoistAuthError(f"Failed to fetch user info: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get user info: {e}")
            raise TodoistAuthError(f"Failed to get user info: {e}")
    
    def get_projects_count(self) -> int:
        """
        Get the number of projects in the user's Todoist account.
        
        Returns:
            Number of projects
            
        Raises:
            TodoistAuthError: If the request fails
        """
        if not self.validate_token():
            raise TodoistAuthError("Invalid API token")
            
        try:
            logger.debug("Fetching Todoist projects count")
            
            response = self.session.get(f"{self.BASE_URL}/projects", timeout=10)
            
            if response.status_code == 200:
                projects = response.json()
                count = len(projects)
                logger.debug(f"Found {count} projects in Todoist")
                return count
            else:
                raise TodoistAuthError(f"Failed to fetch projects: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get projects count: {e}")
            raise TodoistAuthError(f"Failed to get projects count: {e}")
    
    def check_api_rate_limit(self) -> Dict[str, Any]:
        """
        Check current API rate limit status.
        
        Returns:
            Dictionary containing rate limit information
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/projects", timeout=10)
            
            rate_limit_info = {
                'remaining': response.headers.get('X-RateLimit-Remaining'),
                'limit': response.headers.get('X-RateLimit-Limit'),
                'reset': response.headers.get('X-RateLimit-Reset'),
                'status_code': response.status_code
            }
            
            logger.debug(f"Rate limit info: {rate_limit_info}")
            return rate_limit_info
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to check rate limit: {e}")
            return {'error': str(e)}
    
    def validate_connection_detailed(self) -> Dict[str, Any]:
        """
        Perform detailed connection validation with comprehensive information.
        
        Returns:
            Dictionary containing detailed validation results
        """
        result = {
            'token_configured': bool(self.api_token and self.api_token != "your_todoist_token_here"),
            'token_valid': False,
            'connection_successful': False,
            'user_info': None,
            'error': None,
            'rate_limit': None
        }
        
        try:
            if not result['token_configured']:
                result['error'] = "API token not configured"
                return result
            
            # Validate token
            result['token_valid'] = self.validate_token()
            
            if result['token_valid']:
                result['connection_successful'] = True
                
                # Get user info
                try:
                    result['user_info'] = self.get_user_info()
                except TodoistAuthError as e:
                    result['error'] = f"Failed to get user info: {e}"
                
                # Get rate limit info
                result['rate_limit'] = self.check_api_rate_limit()
            
        except TodoistAuthError as e:
            result['error'] = str(e)
        except Exception as e:
            result['error'] = f"Unexpected error: {e}"
            
        return result
    
    @staticmethod
    def get_token_instructions() -> str:
        """Get instructions for obtaining a Todoist API token."""
        return """
To get your Todoist API token:

1. Go to Todoist Settings: https://todoist.com/prefs/integrations
2. Scroll down to the "Developer" section
3. Copy your "API token"
4. Add it to your config.yaml file:
   
   todoist:
     api_token: "your_token_here"

Alternatively, set the environment variable:
   export TODOIST_API_TOKEN="your_token_here"
"""
    
    def update_token(self, new_token: str) -> bool:
        """
        Update the API token and validate it.
        
        Args:
            new_token: The new API token to use
            
        Returns:
            True if the new token is valid, False otherwise
        """
        old_token = self.api_token
        self.api_token = new_token
        
        # Update session headers
        self.session.headers.update({
            'Authorization': f'Bearer {new_token}'
        })
        
        try:
            if self.validate_token():
                logger.info("Successfully updated Todoist API token")
                return True
            else:
                # Revert to old token
                self.api_token = old_token
                self.session.headers.update({
                    'Authorization': f'Bearer {old_token}'
                })
                logger.error("New token is invalid, reverted to old token")
                return False
                
        except TodoistAuthError:
            # Revert to old token
            self.api_token = old_token
            self.session.headers.update({
                'Authorization': f'Bearer {old_token}'
            })
            logger.error("Token validation failed, reverted to old token")
            return False