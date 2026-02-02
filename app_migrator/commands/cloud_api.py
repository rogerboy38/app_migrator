import requests
import json
import base64
from typing import Optional, Dict, Any
import click

class FrappeCloudAPI:
    """Client for Frappe Cloud API."""
    
    BASE_URL = "https://frappecloud.com/api/method"
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.auth_header = self._create_auth_header()
    
    def _create_auth_header(self) -> Dict[str, str]:
        """Create authentication header for Frappe Cloud API."""
        auth_string = f"{self.api_key}:{self.api_secret}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        return {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json"
        }
    
    def get_sites(self) -> Optional[Dict[str, Any]]:
        """Get all sites from Frappe Cloud."""
        try:
            response = requests.post(
                f"{self.BASE_URL}/press.api.site.all",
                headers=self.auth_header,
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get("message", {})
            else:
                click.echo(f"Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            click.echo(f"Error fetching sites: {e}")
            return None
    
    def get_site_info(self, site_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific site."""
        try:
            response = requests.post(
                f"{self.BASE_URL}/press.api.site.get",
                headers=self.auth_header,
                json={"name": site_name},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get("message", {})
            else:
                click.echo(f"Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            click.echo(f"Error fetching site info: {e}")
            return None

class SiteAPI:
    """Client for site-specific REST API."""
    
    def __init__(self, site_url: str, api_key: str, api_secret: str):
        self.base_url = f"https://{site_url.rstrip('/')}"
        self.api_key = api_key
        self.api_secret = api_secret
        self.auth_header = self._create_auth_header()
    
    def _create_auth_header(self) -> Dict[str, str]:
        """Create authentication header for site API."""
        auth_string = f"{self.api_key}:{self.api_secret}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        return {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json"
        }
    
    def ping(self) -> bool:
        """Test connection to site."""
        try:
            response = requests.get(
                f"{self.base_url}/api/method/frappe.ping",
                headers=self.auth_header,
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def get_installed_apps(self) -> Optional[Dict[str, Any]]:
        """Get installed applications from site."""
        try:
            # Method 1: Try via API method
            response = requests.get(
                f"{self.base_url}/api/method/frappe.apps.get_installed_apps",
                headers=self.auth_header,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("message", {})
            
            # Method 2: Try via Resource API
            response = requests.get(
                f"{self.base_url}/api/resource/Installed%20Application",
                headers=self.auth_header,
                params={"fields": '["app_name", "app_version", "app_title"]'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {"data": data.get("data", [])}
            
            return None
            
        except Exception as e:
            click.echo(f"Error fetching installed apps: {e}")
            return None
    
    def get_app_versions(self) -> Dict[str, str]:
        """Get version information for all installed apps."""
        try:
            response = requests.get(
                f"{self.base_url}/api/method/frappe.utils.versions.get_versions",
                headers=self.auth_header,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("message", {})
            else:
                return {}
        except Exception as e:
            click.echo(f"Error fetching app versions: {e}")
            return {}
