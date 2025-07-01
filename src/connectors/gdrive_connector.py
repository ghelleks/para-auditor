"""Google Drive API connector for PARA method folder management."""
import logging
from typing import List, Dict, Optional, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from ..models.para_item import PARAItem, ItemType, ItemSource, CategoryType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GDriveConnector:
    """Connector for Google Drive API to fetch PARA method folders."""
    
    def __init__(self, credentials: Credentials, account_type: str = 'personal'):
        """Initialize Google Drive connector.
        
        Args:
            credentials: Google OAuth2 credentials
            account_type: 'work' or 'personal' for classification
        """
        self.credentials = credentials
        self.account_type = account_type
        self.service = None
        self._initialize_service()
        
    def _initialize_service(self):
        """Initialize Google Drive API service."""
        try:
            # Refresh credentials if needed
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            
            self.service = build('drive', 'v3', credentials=self.credentials)
            logger.info(f"Google Drive service initialized for {self.account_type} account")
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            raise
    
    def get_para_folders(self, base_folder_name: str = '@2-Areas') -> List[PARAItem]:
        """Fetch PARA method folders from Google Drive.
        
        Args:
            base_folder_name: Name of the base folder to search in
            
        Returns:
            List of PARAItem objects representing Google Drive folders
        """
        try:
            # First, find the base folder
            logger.debug(f"Searching for base folder '{base_folder_name}' in {self.account_type} Google Drive")
            base_folder = self._find_folder_by_name(base_folder_name)
            if not base_folder:
                logger.warning(f"Base folder '{base_folder_name}' not found in {self.account_type} Google Drive")
                logger.info(f"Tip: Make sure the folder '{base_folder_name}' exists in your Google Drive")
                logger.info(f"You can customize the folder name in config.yaml under google_drive.base_folder_name")
                return []
            
            logger.info(f"Found base folder '{base_folder_name}' (ID: {base_folder['id']}) in {self.account_type} Google Drive")
            
            # Get all folders within the base folder
            folders = self._get_folders_in_directory(base_folder['id'])
            para_items = []
            
            for folder in folders:
                # Determine if folder is active (starred)
                is_active = folder.get('starred', False)
                
                # Check if this is a shortcut
                is_shortcut = folder.get('mimeType') == 'application/vnd.google-apps.shortcut'
                
                # For shortcuts, we need to get the target information
                metadata = {
                    'folder_id': folder['id'],
                    'parent_id': base_folder['id'],
                    'web_view_link': folder.get('webViewLink'),
                    'created_time': folder.get('createdTime'),
                    'modified_time': folder.get('modifiedTime'),
                    'account_type': self.account_type,
                    'is_shortcut': is_shortcut
                }
                
                if is_shortcut:
                    # Add shortcut-specific metadata
                    shortcut_details = folder.get('shortcutDetails', {})
                    metadata.update({
                        'shortcut_target_id': shortcut_details.get('targetId'),
                        'shortcut_target_mime_type': shortcut_details.get('targetMimeType'),
                        'original_folder_name': folder['name']
                    })
                    
                    # Log that we found a shortcut
                    logger.debug(f"Found shortcut '{folder['name']}' pointing to {shortcut_details.get('targetId', 'unknown target')}")
                
                para_item = PARAItem(
                    name=folder['name'],
                    type=ItemType.PROJECT if is_active else ItemType.AREA,
                    is_active=is_active,
                    category=CategoryType.WORK if self.account_type == 'work' else CategoryType.PERSONAL,
                    source=ItemSource.GDRIVE_WORK if self.account_type == 'work' else ItemSource.GDRIVE_PERSONAL,
                    metadata=metadata
                )
                para_items.append(para_item)
            
            # Count shortcuts vs regular folders for logging
            shortcut_count = sum(1 for item in para_items if item.metadata.get('is_shortcut', False))
            folder_count = len(para_items) - shortcut_count
            
            if shortcut_count > 0:
                logger.info(f"Fetched {len(para_items)} items from {self.account_type} Google Drive ({folder_count} folders, {shortcut_count} shortcuts)")
            else:
                logger.info(f"Fetched {len(para_items)} folders from {self.account_type} Google Drive")
            
            return para_items
            
        except Exception as e:
            logger.error(f"Error fetching Google Drive folders: {e}")
            raise
    
    def _find_folder_by_name(self, folder_name: str) -> Optional[Dict[str, Any]]:
        """Find a folder by name in Google Drive.
        
        Args:
            folder_name: Name of the folder to find
            
        Returns:
            Folder metadata dict or None if not found
        """
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = self.service.files().list(
                q=query,
                fields='files(id, name, parents, webViewLink)'
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                return folders[0]  # Return first match
            return None
            
        except HttpError as e:
            logger.error(f"Error searching for folder '{folder_name}': {e}")
            return None
    
    def _get_folders_in_directory(self, parent_id: str) -> List[Dict[str, Any]]:
        """Get all folders within a specific parent directory.
        
        Args:
            parent_id: ID of the parent folder
            
        Returns:
            List of folder metadata dictionaries
        """
        try:
            folders = []
            page_token = None
            
            while True:
                # Include both folders and shortcuts
                query = f"'{parent_id}' in parents and (mimeType='application/vnd.google-apps.folder' or mimeType='application/vnd.google-apps.shortcut') and trashed=false"
                
                results = self.service.files().list(
                    q=query,
                    fields='nextPageToken, files(id, name, starred, webViewLink, createdTime, modifiedTime, parents, mimeType, shortcutDetails)',
                    pageToken=page_token,
                    pageSize=100  # Handle pagination
                ).execute()
                
                batch_folders = results.get('files', [])
                folders.extend(batch_folders)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            return folders
            
        except HttpError as e:
            logger.error(f"Error fetching folders from directory {parent_id}: {e}")
            return []
    
    def get_folder_by_id(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """Get folder metadata by ID.
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            Folder metadata dict or None if not found
        """
        try:
            folder = self.service.files().get(
                fileId=folder_id,
                fields='id, name, starred, webViewLink, createdTime, modifiedTime, parents'
            ).execute()
            
            return folder
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Folder {folder_id} not found")
                return None
            logger.error(f"Error fetching folder {folder_id}: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test connection to Google Drive API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to list a few files to test connection
            results = self.service.files().list(
                pageSize=5,
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Google Drive connection successful for {self.account_type} account. Found {len(files)} sample files.")
            return True
            
        except Exception as e:
            logger.error(f"Google Drive connection failed for {self.account_type} account: {e}")
            return False
    
    def create_folder(self, name: str, parent_id: str = None) -> Optional[str]:
        """Create a new folder in Google Drive.
        
        Args:
            name: Name of the folder to create
            parent_id: ID of parent folder (optional)
            
        Returns:
            ID of created folder or None if failed
        """
        try:
            folder_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                folder_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Created folder '{name}' with ID {folder_id}")
            return folder_id
            
        except HttpError as e:
            logger.error(f"Error creating folder '{name}': {e}")
            return None
    
    def star_folder(self, folder_id: str, starred: bool = True) -> bool:
        """Star or unstar a folder.
        
        Args:
            folder_id: ID of folder to star/unstar
            starred: True to star, False to unstar
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.files().update(
                fileId=folder_id,
                body={'starred': starred}
            ).execute()
            
            action = 'starred' if starred else 'unstarred'
            logger.info(f"Successfully {action} folder {folder_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Error starring folder {folder_id}: {e}")
            return False
    
    def create_shortcut(self, target_id: str, name: str, parent_id: str = None) -> Optional[str]:
        """Create a shortcut to a folder in Google Drive.
        
        Args:
            target_id: ID of the target folder to create shortcut to
            name: Name for the shortcut
            parent_id: ID of parent folder (optional)
            
        Returns:
            ID of created shortcut or None if failed
        """
        try:
            shortcut_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.shortcut',
                'shortcutDetails': {
                    'targetId': target_id
                }
            }
            
            if parent_id:
                shortcut_metadata['parents'] = [parent_id]
            
            shortcut = self.service.files().create(
                body=shortcut_metadata,
                fields='id'
            ).execute()
            
            shortcut_id = shortcut.get('id')
            logger.info(f"Created shortcut '{name}' with ID {shortcut_id} pointing to {target_id}")
            return shortcut_id
            
        except HttpError as e:
            logger.error(f"Error creating shortcut '{name}': {e}")
            return None
