import os
import subprocess
import tempfile
from pathlib import Path
import click

class SSHManager:
    def __init__(self):
        self.ssh_dir = Path.home() / ".ssh"
        self.ssh_dir.mkdir(mode=0o700, exist_ok=True)
    
    def check_ssh_status(self):
        """Check SSH key status and GitHub connectivity"""
        status = {
            "has_ssh_keys": False,
            "github_connected": False,
            "keys": []
        }
        
        # Check for SSH keys
        key_patterns = ["id_ed25519", "id_rsa", "id_ecdsa", "id_dsa"]
        for pattern in key_patterns:
            private_key = self.ssh_dir / pattern
            public_key = self.ssh_dir / f"{pattern}.pub"
            
            if private_key.exists() and public_key.exists():
                status["has_ssh_keys"] = True
                status["keys"].append({
                    "type": pattern,
                    "private": str(private_key),
                    "public": str(public_key)
                })
        
        # Test GitHub connection
        status["github_connected"] = self.test_github_connection()
        
        return status
    
    def test_github_connection(self, key_path=None):
        """Test SSH connection to GitHub"""
        try:
            # Test with a simple command
            cmd = ["ssh", "-T", "git@github.com"]
            if key_path:
                cmd = ["ssh", "-i", key_path, "-T", "git@github.com"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # GitHub returns success even with "Hi username!" message
            if result.returncode == 1 and "successfully authenticated" in result.stderr:
                return True
            elif result.returncode == 0:
                return True
            else:
                return False
                
        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            print(f"SSH test error: {e}")
            return False
    
    def create_ssh_key(self, key_type="ed25519", comment="frappe-cloud-migration"):
        """Create new SSH key pair"""
        key_name = f"frappe_migrator_{key_type}"
        key_path = self.ssh_dir / key_name
        
        # Check if key already exists
        if key_path.exists():
            click.echo(f"⚠️  Key already exists: {key_path}")
            if not click.confirm("Overwrite?"):
                return str(key_path)
        
        # Create key
        cmd = [
            "ssh-keygen",
            "-t", key_type,
            "-C", f"{comment}-{subprocess.getoutput('date +%Y%m%d')}",
            "-f", str(key_path),
            "-N", ""  # No passphrase for automation
        ]
        
        try:
            subprocess.run(cmd, check=True)
            
            # Set proper permissions
            os.chmod(key_path, 0o600)
            os.chmod(f"{key_path}.pub", 0o644)
            
            # Add to ssh-agent
            self.add_to_ssh_agent(str(key_path))
            
            return str(key_path)
            
        except subprocess.CalledProcessError as e:
            click.echo(f"❌ Failed to create SSH key: {e}")
            return None
    
    def add_to_ssh_agent(self, key_path):
        """Add SSH key to ssh-agent"""
        try:
            # Start ssh-agent if not running
            subprocess.run(["ssh-add", "-l"], capture_output=True)
            
            # Add the key
            result = subprocess.run(
                ["ssh-add", key_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                click.echo("✅ Added key to ssh-agent")
                return True
            else:
                click.echo(f"⚠️  Could not add to ssh-agent: {result.stderr}")
                return False
                
        except Exception as e:
            click.echo(f"⚠️  SSH agent error: {e}")
            return False
    
    def get_public_key(self, key_path=None):
        """Get public key content"""
        if not key_path:
            # Try to find a key
            status = self.check_ssh_status()
            if status["keys"]:
                key_path = status["keys"][0]["private"]
        
        if not key_path:
            return None
        
        pub_key_path = f"{key_path}.pub"
        if os.path.exists(pub_key_path):
            with open(pub_key_path, "r") as f:
                return f.read().strip()
        
        return None
    
    def copy_key_to_target(self, source_key_path, target_bench_path):
        """Copy SSH key to target bench"""
        target_ssh_dir = Path(target_bench_path) / ".ssh"
        target_ssh_dir.mkdir(mode=0o700, exist_ok=True)
        
        key_name = os.path.basename(source_key_path)
        target_key_path = target_ssh_dir / key_name
        
        # Copy private key
        import shutil
        shutil.copy2(source_key_path, target_key_path)
        os.chmod(target_key_path, 0o600)
        
        # Copy public key
        pub_source = f"{source_key_path}.pub"
        pub_target = f"{target_key_path}.pub"
        if os.path.exists(pub_source):
            shutil.copy2(pub_source, pub_target)
            os.chmod(pub_target, 0o644)
        
        return str(target_key_path)
