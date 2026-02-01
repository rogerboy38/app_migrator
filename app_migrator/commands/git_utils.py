"""
Git Utilities for Frappe Apps - Integration with Frappe Cloud API
"""

import os
import requests
import json
from pathlib import Path
from typing import Optional, Dict, List
import subprocess
import click


class FrappeCloudAPI:
    """Interface to Frappe Cloud API for getting app git info"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('FRAPPE_CLOUD_API_KEY')
        self.base_url = "https://frappecloud.com"
        
    def get_app_git_info(self, app_name: str) -> Optional[Dict]:
        """Get git repository information for an app from Frappe Cloud"""
        if not self.api_key:
            return None
            
        try:
            headers = {
                'Authorization': f'token {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Try to get app info from Frappe Cloud marketplace
            response = requests.get(
                f'{self.base_url}/api/method/apps',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                apps_data = response.json().get('message', [])
                for app in apps_data:
                    if app.get('name') == app_name:
                        return {
                            'git_url': app.get('git_url'),
                            'branch': app.get('branch', 'main'),
                            'version': app.get('version'),
                            'is_public': app.get('is_public', False)
                        }
        except Exception as e:
            click.echo(f"⚠️  Frappe Cloud API error: {str(e)}")
        
        return None
    
    def get_public_app_git_url(self, app_name: str) -> Optional[str]:
        """Get git URL for public Frappe apps (no API key needed)"""
        # Common public app repositories
        public_apps = {
            'erpnext': 'https://github.com/frappe/erpnext',
            'hrms': 'https://github.com/frappe/hrms',
            'payments': 'https://github.com/frappe/payments',
            'frappe': 'https://github.com/frappe/frappe',
            'crm': 'https://github.com/frappe/crm',
            'insights': 'https://github.com/frappe/insights',
            'lms': 'https://github.com/frappe/lms',
            'helpdesk': 'https://github.com/frappe/helpdesk',
            'raven': 'https://github.com/frappe/raven',
            'print_designer': 'https://github.com/frappe/print_designer',
            'builder': 'https://github.com/frappe/builder',
            'telephony': 'https://github.com/frappe/telephony',
            'drive': 'https://github.com/frappe/drive',
        }
        
        return public_apps.get(app_name)


def get_app_info(app_name: str, api_key: Optional[str] = None) -> Dict:
    """Get comprehensive information about an app"""
    bench_path = Path(os.getenv('BENCH_PATH', '/home/frappe/frappe-bench'))
    app_path = bench_path / 'apps' / app_name
    
    info = {
        'name': app_name,
        'path': str(app_path),
        'exists': app_path.exists(),
        'is_git_repo': False,
        'has_remote': False,
        'remote_url': None,
        'branch': None,
        'git_available': False,
        'frappe_cloud_info': None,
        'public_git_url': None
    }
    
    if not app_path.exists():
        return info
    
    # Check if it's a git repo
    git_dir = app_path / '.git'
    info['is_git_repo'] = git_dir.exists()
    
    if info['is_git_repo']:
        # Get git remote
        try:
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                cwd=app_path,
                capture_output=True,
                text=True,
                check=False
            )
            info['remote_url'] = result.stdout.strip() if result.stdout.strip() else None
            info['has_remote'] = bool(info['remote_url'])
            
            # Get current branch
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=app_path,
                capture_output=True,
                text=True,
                check=False
            )
            info['branch'] = result.stdout.strip() if result.stdout.strip() else None
            
            info['git_available'] = True
            
        except Exception:
            pass
    
    # Get Frappe Cloud info if API key available
    if api_key:
        cloud_api = FrappeCloudAPI(api_key)
        info['frappe_cloud_info'] = cloud_api.get_app_git_info(app_name)
    
    # Get public git URL
    cloud_api = FrappeCloudAPI()
    info['public_git_url'] = cloud_api.get_public_app_git_url(app_name)
    
    return info


def clone_app_from_git(app_name: str, git_url: str, branch: str = 'main') -> bool:
    """Clone an app from git repository"""
    bench_path = Path(os.getenv('BENCH_PATH', '/home/frappe/frappe-bench'))
    app_path = bench_path / 'apps' / app_name
    
    if app_path.exists():
        click.echo(f"⚠️  App directory already exists: {app_name}")
        return False
    
    try:
        click.echo(f"📥 Cloning {app_name} from {git_url} (branch: {branch})...")
        
        # Clone the repository
        result = subprocess.run(
            ['git', 'clone', '-b', branch, git_url, str(app_path)],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            click.echo(f"✅ Successfully cloned {app_name}")
            return True
        else:
            click.echo(f"❌ Failed to clone {app_name}: {result.stderr}")
            return False
            
    except Exception as e:
        click.echo(f"❌ Error cloning {app_name}: {str(e)}")
        return False


def convert_to_git_repo(app_name: str, git_url: Optional[str] = None) -> bool:
    """Convert a non-git app directory to a git repository"""
    bench_path = Path(os.getenv('BENCH_PATH', '/home/frappe/frappe-bench'))
    app_path = bench_path / 'apps' / app_name
    
    if not app_path.exists():
        click.echo(f"❌ App directory not found: {app_name}")
        return False
    
    # Check if already a git repo
    if (app_path / '.git').exists():
        click.echo(f"⚠️  {app_name} is already a git repository")
        return True
    
    try:
        click.echo(f"🔄 Converting {app_name} to git repository...")
        
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=app_path, check=True)
        subprocess.run(['git', 'add', '.'], cwd=app_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=app_path, check=True)
        
        # Add remote if URL provided
        if git_url:
            subprocess.run(['git', 'remote', 'add', 'origin', git_url], cwd=app_path, check=True)
            click.echo(f"✅ Added remote: {git_url}")
        
        click.echo(f"✅ Successfully converted {app_name} to git repository")
        return True
        
    except Exception as e:
        click.echo(f"❌ Error converting {app_name}: {str(e)}")
        return False
