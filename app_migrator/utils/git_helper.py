import subprocess
import shlex
from typing import Dict, List, Tuple, Optional

class GitHelper:
    @staticmethod
    def get_remotes() -> Dict[str, str]:
        """Get all remote URLs"""
        cmd = "git remote -v"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        remotes = {}
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    remote_name = parts[0]
                    remote_url = parts[1]
                    if '(push)' in line:
                        remotes[remote_name] = remote_url
        return remotes
    # Add to your existing git_helper.py in app_migrator/utils/
    @staticmethod
    def has_uncommitted_changes() -> bool:
        """Check if there are uncommitted changes"""
        cmd = "git status --porcelain"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return bool(result.stdout.strip())
    
    @staticmethod
    def stage_and_commit(message: str) -> bool:
        """Stage and commit all changes"""
        try:
            subprocess.run("git add .", shell=True, check=True)
            subprocess.run(f'git commit -m "{message}"', shell=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def push_to_remote(remote: str, branch: str, force: bool = False) -> bool:
        """Push to a specific remote"""
        try:
            force_flag = "--force" if force else ""
            cmd = f"git push {force_flag} {remote} {branch}"
            subprocess.run(cmd, shell=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def pull_from_remote(remote: str, branch: str) -> bool:
        """Pull from a specific remote"""
        try:
            cmd = f"git pull {remote} {branch}"
            subprocess.run(cmd, shell=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def get_common_ancestor(local_hash: str, remote_hash: str) -> str:
        """Get common ancestor commit hash"""
        cmd = f"git merge-base {local_hash} {remote_hash}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()

    @staticmethod
    def get_current_branch() -> str:
        """Get current branch name"""
        cmd = "git rev-parse --abbrev-ref HEAD"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    
    @staticmethod
    def get_branch_status(remote: str, branch: str) -> Dict[str, str]:
        """
        Check git status compared to remote
        Returns: {
            'local': 'commit_hash',
            'remote': 'commit_hash',
            'base': 'common_ancestor',
            'status': 'ahead|behind|diverged|same|no_remote'
        }
        """
        # First, fetch the remote
        subprocess.run(f"git fetch {remote}", shell=True, capture_output=True)
        
        # Get local commit
        cmd_local = f"git rev-parse {branch}"
        result_local = subprocess.run(cmd_local, shell=True, capture_output=True, text=True)
        local_hash = result_local.stdout.strip() if result_local.returncode == 0 else None
        
        # Get remote commit
        cmd_remote = f"git rev-parse {remote}/{branch}"
        result_remote = subprocess.run(cmd_remote, shell=True, capture_output=True, text=True)
        remote_hash = result_remote.stdout.strip() if result_remote.returncode == 0 else None
        
        if not remote_hash:
            return {'status': 'no_remote', 'local': local_hash, 'remote': None}
        
        if local_hash == remote_hash:
            return {'status': 'same', 'local': local_hash, 'remote': remote_hash}
        
        # Check if we can fast-forward (local is ahead)
        cmd_ahead = f"git rev-list --count {remote_hash}..{local_hash}"
        result_ahead = subprocess.run(cmd_ahead, shell=True, capture_output=True, text=True)
        ahead_count = int(result_ahead.stdout.strip()) if result_ahead.returncode == 0 else 0
        
        # Check if remote is ahead (we're behind)
        cmd_behind = f"git rev-list --count {local_hash}..{remote_hash}"
        result_behind = subprocess.run(cmd_behind, shell=True, capture_output=True, text=True)
        behind_count = int(result_behind.stdout.strip()) if result_behind.returncode == 0 else 0
        
        if ahead_count > 0 and behind_count == 0:
            return {'status': 'ahead', 'local': local_hash, 'remote': remote_hash, 'count': ahead_count}
        elif behind_count > 0 and ahead_count == 0:
            return {'status': 'behind', 'local': local_hash, 'remote': remote_hash, 'count': behind_count}
        elif ahead_count > 0 and behind_count > 0:
            return {'status': 'diverged', 'local': local_hash, 'remote': remote_hash, 
                    'ahead': ahead_count, 'behind': behind_count}
        
        return {'status': 'unknown', 'local': local_hash, 'remote': remote_hash}
