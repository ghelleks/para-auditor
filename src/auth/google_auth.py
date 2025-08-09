"""Google OAuth authentication for Drive API access."""

import os
import pickle
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


logger = logging.getLogger(__name__)


class GoogleAuthError(Exception):
    """Custom exception for Google authentication errors."""
    pass


class GoogleAuthenticator:
    """Handles Google OAuth authentication for Drive API access."""
    
    def __init__(self, config_manager):
        """Initialize with configuration manager."""
        self.config_manager = config_manager
        self.scopes = config_manager.google_scopes
        self.credentials_dir = Path("config/credentials")
        
        # Account-specific client secrets files from configuration
        self.client_secrets_paths = {
            'work': Path(config_manager.work_client_secrets_path),
            'personal': Path(config_manager.personal_client_secrets_path)
        }
        
        # Ensure credentials directory exists
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        
    def authenticate_account(self, account_type: str) -> Credentials:
        """
        Authenticate a Google account (work or personal).
        
        Args:
            account_type: Either 'work' or 'personal'
            
        Returns:
            Google OAuth credentials
            
        Raises:
            GoogleAuthError: If authentication fails
        """
        if account_type not in ['work', 'personal']:
            raise GoogleAuthError(f"Invalid account type: {account_type}")
            
        logger.info(f"Authenticating {account_type} Google account")
        
        # Check for existing credentials
        token_path = self.credentials_dir / f"{account_type}_drive_token.pickle"
        creds = self._load_existing_credentials(token_path)
        
        if creds and creds.valid:
            logger.info(f"Using existing valid credentials for {account_type} account")
            return creds
            
        # Refresh credentials if they exist but are expired
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info(f"Refreshing expired credentials for {account_type} account")
                creds.refresh(Request())
                self._save_credentials(creds, token_path)
                return creds
            except Exception as e:
                logger.warning(f"Failed to refresh credentials: {e}")
                # Continue to re-authenticate
                
        # Perform OAuth flow for new/invalid credentials
        creds = self._perform_oauth_flow(account_type)
        self._save_credentials(creds, token_path)
        
        return creds
    
    def _load_existing_credentials(self, token_path: Path) -> Optional[Credentials]:
        """Load existing credentials from file."""
        if not token_path.exists():
            return None
            
        try:
            with open(token_path, 'rb') as token_file:
                creds = pickle.load(token_file)
                logger.debug(f"Loaded credentials from {token_path}")
                return creds
        except Exception as e:
            logger.warning(f"Failed to load credentials from {token_path}: {e}")
            return None
    
    def _save_credentials(self, creds: Credentials, token_path: Path):
        """Save credentials to file."""
        try:
            with open(token_path, 'wb') as token_file:
                pickle.dump(creds, token_file)
                logger.debug(f"Saved credentials to {token_path}")
        except Exception as e:
            logger.error(f"Failed to save credentials to {token_path}: {e}")
            raise GoogleAuthError(f"Failed to save credentials: {e}")
    
    def _perform_oauth_flow(self, account_type: str) -> Credentials:
        """Perform OAuth flow for the specified account type."""
        client_secrets_path = self.client_secrets_paths[account_type]
        
        if not client_secrets_path.exists():
            raise GoogleAuthError(
                f"Client secrets file not found at {client_secrets_path}. "
                f"Please download the {account_type} account client secrets from Google Cloud Console "
                f"and save it as {client_secrets_path.name} in the config/credentials/ directory."
            )
        
        try:
            # Create flow from client secrets
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets_path), 
                self.scopes
            )
            
            # Get domain hint for the account type
            domain_hint = self._get_domain_hint(account_type)
            
            # Customize authorization URL
            authorization_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='select_account',
                hd=domain_hint  # Domain hint to suggest the right account
            )
            
            logger.info(f"Starting OAuth flow for {account_type} account")
            print(f"\n🔐 Authenticating {account_type.title()} Google Account")
            print(f"Please sign in to your {account_type} account ({domain_hint})")
            print("Your browser will open automatically...")
            
            # Run local server to handle OAuth callback
            creds = flow.run_local_server(
                port=0,
                prompt='select_account',
                authorization_prompt_message=f'Please sign in to your {account_type} Google account'
            )
            
            # Validate the authenticated account
            self._validate_account_domain(creds, account_type)
            
            logger.info(f"Successfully authenticated {account_type} account")
            print(f"✅ Successfully authenticated {account_type} account")
            
            return creds
            
        except Exception as e:
            logger.error(f"OAuth flow failed for {account_type} account: {e}")
            # Provide actionable guidance for common OAuth issues
            hint_lines = self._build_oauth_error_hint(str(e), account_type, client_secrets_path)
            hint = "\n" + "\n".join(hint_lines) if hint_lines else ""
            raise GoogleAuthError(f"OAuth flow failed: {e}{hint}")
    
    def _get_domain_hint(self, account_type: str) -> str:
        """Get domain hint for the account type."""
        if account_type == 'work':
            domain = self.config_manager.work_domain
        else:
            domain = self.config_manager.personal_domain
            
        # Remove @ prefix if present
        return domain.lstrip('@') if domain else ''

    def _build_oauth_error_hint(self, error_text: str, account_type: str, client_secrets_path: Path):
        """Build user-facing hints for common OAuth failures."""
        hints = []
        prefix = f"[{account_type} Google Drive]"

        # General reminder
        hints.append(f"{prefix} Verify your OAuth client secrets file path in config: {client_secrets_path}")

        # Invalid client / unauthorized client issues
        lowered = error_text.lower()
        if 'invalid_client' in lowered or 'unauthorized' in lowered or 'unauthorized_client' in lowered:
            hints.append(f"{prefix} Ensure you created 'Desktop application' OAuth 2.0 credentials (Installed app), not Web/iOS/Android.")
            hints.append(f"{prefix} The credentials JSON should contain an 'installed' block with redirect_uris including 'http://localhost'.")
            hints.append(f"{prefix} Re-download the JSON from Google Cloud Console and replace: {client_secrets_path}")
            hints.append(f"{prefix} Make sure the Google Cloud project and OAuth client have not been deleted or restricted.")

        # Consent screen / test users
        hints.append(f"{prefix} Confirm OAuth consent screen is configured and your account is allowed (if app is in Testing).")

        # Final step
        hints.append(f"{prefix} Then run: para-auditor --setup and sign in with the correct {account_type} account.")

        return hints
    
    def _validate_account_domain(self, creds: Credentials, account_type: str):
        """Validate that the authenticated account matches the expected domain."""
        try:
            # Build a service to get user info
            service = build('oauth2', 'v2', credentials=creds)
            user_info = service.userinfo().get().execute()
            
            email = user_info.get('email', '')
            expected_domain = self._get_domain_hint(account_type)
            
            if expected_domain and not email.endswith(f"@{expected_domain}"):
                logger.warning(
                    f"Account domain mismatch: got {email}, expected domain @{expected_domain}"
                )
                print(f"⚠️  Warning: Authenticated account ({email}) doesn't match expected domain (@{expected_domain})")
                
                # Ask user if they want to continue
                response = input("Continue anyway? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    raise GoogleAuthError("Authentication cancelled due to domain mismatch")
            
            logger.info(f"Validated {account_type} account: {email}")
            
        except HttpError as e:
            logger.warning(f"Could not validate account domain: {e}")
            # Continue anyway - domain validation is not critical
    
    def get_credentials(self, account_type: str) -> Credentials:
        """Get credentials for the specified account type.
        
        Args:
            account_type: Either 'work' or 'personal'
            
        Returns:
            Google OAuth credentials
            
        Raises:
            GoogleAuthError: If authentication fails
        """
        return self.authenticate_account(account_type)

    def get_drive_service(self, account_type: str):
        """Get an authenticated Google Drive service."""
        creds = self.authenticate_account(account_type)
        
        try:
            service = build('drive', 'v3', credentials=creds)
            logger.debug(f"Created Drive service for {account_type} account")
            return service
        except Exception as e:
            logger.error(f"Failed to create Drive service: {e}")
            raise GoogleAuthError(f"Failed to create Drive service: {e}")
    
    def test_connection(self, account_type: str) -> bool:
        """Test connection to Google Drive for the specified account."""
        try:
            service = self.get_drive_service(account_type)
            
            # Try to list a single file to test the connection
            results = service.files().list(pageSize=1).execute()
            
            logger.info(f"Successfully tested {account_type} Drive connection")
            return True
            
        except Exception as e:
            logger.error(f"Drive connection test failed for {account_type}: {e}")
            return False
    
    def revoke_credentials(self, account_type: str) -> bool:
        """Revoke stored credentials for an account."""
        token_path = self.credentials_dir / f"{account_type}_drive_token.pickle"
        
        try:
            if token_path.exists():
                # Load credentials and revoke them
                creds = self._load_existing_credentials(token_path)
                if creds:
                    try:
                        # Revoke the credentials on Google's side
                        service = build('oauth2', 'v2', credentials=creds)
                        service.revoke().execute()
                        logger.info(f"Revoked credentials on Google's side for {account_type}")
                    except Exception as e:
                        logger.warning(f"Failed to revoke credentials on Google's side: {e}")
                
                # Remove the local token file
                token_path.unlink()
                logger.info(f"Removed local credentials for {account_type}")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke credentials for {account_type}: {e}")
            return False
    
    def get_account_info(self, account_type: str) -> Dict[str, Any]:
        """Get information about the authenticated account."""
        try:
            creds = self.authenticate_account(account_type)
            service = build('oauth2', 'v2', credentials=creds)
            user_info = service.userinfo().get().execute()
            
            return {
                'email': user_info.get('email', ''),
                'name': user_info.get('name', ''),
                'picture': user_info.get('picture', ''),
                'account_type': account_type
            }
            
        except Exception as e:
            logger.error(f"Failed to get account info for {account_type}: {e}")
            return {'error': str(e), 'account_type': account_type}
    
    def is_authenticated(self, account_type: str) -> bool:
        """Check if account is already authenticated with valid credentials."""
        token_path = self.credentials_dir / f"{account_type}_drive_token.pickle"
        
        if not token_path.exists():
            return False
            
        creds = self._load_existing_credentials(token_path)
        if not creds:
            return False
            
        # Check if credentials are valid or can be refreshed
        if creds.valid:
            return True
            
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_credentials(creds, token_path)
                return True
            except Exception:
                return False
                
        return False