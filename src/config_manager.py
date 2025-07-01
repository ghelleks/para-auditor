"""Configuration management for PARA Auditor."""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigError(Exception):
    """Custom exception for configuration-related errors."""
    pass


class ConfigManager:
    """Manages configuration loading, validation, and access."""
    
    DEFAULT_CONFIG_PATH = "config/config.yaml"
    DEFAULT_CONFIG_TEMPLATE = {
        "todoist": {
            "api_token": "your_todoist_token_here"
        },
        "google_drive": {
            "work_account_domain": "@yourcompany.com",
            "personal_account_domain": "@gmail.com",
            "scopes": [
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/drive.metadata.readonly"
            ]
        },
        "apple_notes": {
            "projects_folder": "Projects",
            "areas_folder": "Areas"
        },
        "audit_settings": {
            "similarity_threshold": 0.8,
            "report_format": "markdown"
        }
    }
    
    REQUIRED_FIELDS = [
        "todoist.api_token",
        "google_drive.work_account_domain",
        "google_drive.personal_account_domain",
        "apple_notes.projects_folder",
        "apple_notes.areas_folder"
    ]
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize ConfigManager with optional custom config path."""
        self.config_path = Path(config_path or self.DEFAULT_CONFIG_PATH)
        self.config_data: Dict[str, Any] = {}
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment variables."""
        if not self.config_path.exists():
            raise ConfigError(f"Configuration file not found: {self.config_path}")
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config_data = yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in config file: {e}")
        except Exception as e:
            raise ConfigError(f"Error reading config file: {e}")
            
        # Override with environment variables if they exist
        self._load_env_overrides()
        
        # Validate configuration
        self._validate_config()
        
        return self.config_data
    
    def _load_env_overrides(self):
        """Load configuration overrides from environment variables."""
        env_mappings = {
            "TODOIST_API_TOKEN": "todoist.api_token",
            "WORK_ACCOUNT_DOMAIN": "google_drive.work_account_domain",
            "PERSONAL_ACCOUNT_DOMAIN": "google_drive.personal_account_domain",
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested_value(self.config_data, config_path, value)
    
    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any):
        """Set a nested dictionary value using dot notation."""
        keys = path.split('.')
        current = data
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
            
        # Set the final value
        current[keys[-1]] = value
    
    def _validate_config(self):
        """Validate required configuration fields are present."""
        missing_fields = []
        
        for field_path in self.REQUIRED_FIELDS:
            if not self._get_nested_value(self.config_data, field_path):
                missing_fields.append(field_path)
        
        if missing_fields:
            raise ConfigError(f"Missing required configuration fields: {', '.join(missing_fields)}")
            
        # Validate specific field formats
        self._validate_field_formats()
    
    def _validate_field_formats(self):
        """Validate specific field formats and values."""
        # Check domain formats
        work_domain = self.get("google_drive.work_account_domain")
        personal_domain = self.get("google_drive.personal_account_domain")
        
        if work_domain and not work_domain.startswith("@"):
            raise ConfigError("Work account domain must start with '@'")
            
        if personal_domain and not personal_domain.startswith("@"):
            raise ConfigError("Personal account domain must start with '@'")
            
        # Check similarity threshold
        threshold = self.get("audit_settings.similarity_threshold")
        if threshold and (not isinstance(threshold, (int, float)) or threshold < 0 or threshold > 1):
            raise ConfigError("Similarity threshold must be a number between 0 and 1")
            
        # Check report format
        report_format = self.get("audit_settings.report_format")
        valid_formats = ["markdown", "json", "text"]
        if report_format and report_format not in valid_formats:
            raise ConfigError(f"Report format must be one of: {', '.join(valid_formats)}")
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get a nested dictionary value using dot notation."""
        keys = path.split('.')
        current = data
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return None
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation."""
        value = self._get_nested_value(self.config_data, path)
        return value if value is not None else default
    
    def create_default_config(self, force: bool = False):
        """Create a default configuration file."""
        if self.config_path.exists() and not force:
            raise ConfigError(f"Configuration file already exists: {self.config_path}")
            
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.dump(self.DEFAULT_CONFIG_TEMPLATE, file, default_flow_style=False, indent=2)
        except Exception as e:
            raise ConfigError(f"Error creating default config file: {e}")
    
    def is_configured(self) -> bool:
        """Check if the application is properly configured."""
        try:
            self.load_config()
            return True
        except ConfigError:
            return False
    
    @property
    def todoist_token(self) -> str:
        """Get Todoist API token."""
        return self.get("todoist.api_token", "")
    
    @property
    def work_domain(self) -> str:
        """Get work account domain."""
        return self.get("google_drive.work_account_domain", "")
    
    @property
    def personal_domain(self) -> str:
        """Get personal account domain."""
        return self.get("google_drive.personal_account_domain", "")
    
    @property
    def google_scopes(self) -> list:
        """Get Google Drive API scopes."""
        return self.get("google_drive.scopes", [])
    
    @property
    def work_client_secrets_path(self) -> str:
        """Get work account client secrets file path."""
        return self.get("google_drive.work_client_secrets", "config/credentials/work_client_secrets.json")
    
    @property
    def personal_client_secrets_path(self) -> str:
        """Get personal account client secrets file path."""
        return self.get("google_drive.personal_client_secrets", "config/credentials/personal_client_secrets.json")
    
    @property
    def gdrive_base_folder_name(self) -> str:
        """Get Google Drive base folder name."""
        return self.get("google_drive.base_folder_name", "@2-Areas")
    
    @property
    def projects_folder(self) -> str:
        """Get Apple Notes projects folder name."""
        return self.get("apple_notes.projects_folder", "Projects")
    
    @property
    def areas_folder(self) -> str:
        """Get Apple Notes areas folder name."""
        return self.get("apple_notes.areas_folder", "Areas")
    
    @property
    def similarity_threshold(self) -> float:
        """Get name similarity threshold."""
        return self.get("audit_settings.similarity_threshold", 0.8)
    
    @property
    def report_format(self) -> str:
        """Get report output format."""
        return self.get("audit_settings.report_format", "markdown")