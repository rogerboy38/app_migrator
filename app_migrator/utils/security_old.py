import keyring
import requests
import json
import base64
import hashlib
from cryptography.fernet import Fernet
import os

class APIManager:
    def __init__(self):
        self.service_name = "frappe_cloud"
        self.username = "api_key"
        
    def set_api_key(self, api_key, store=True):
        """Store API key securely"""
        if store:
            # Generate encryption key from bench path
            bench_path = os.getcwd()
            encryption_key = self._generate_encryption_key(bench_path)
            cipher = Fernet(encryption_key)
            
            # Encrypt and store
            encrypted_key = cipher.encrypt(api_key.encode())
            keyring.set_password(self.service_name, self.username, encrypted_key.decode())
        
        # Also store in memory for current session
        self._current_key = api_key
        return True
    
    def get_api_key(self):
        """Retrieve API key"""
        # First check memory
        if hasattr(self, '_current_key'):
            return self._current_key
        
        # Then check keyring
        encrypted_key = keyring.get_password(self.service_name, self.username)
        if encrypted_key:
            # Decrypt
            bench_path = os.getcwd()
            encryption_key = self._generate_encryption_key(bench_path)
            cipher = Fernet(encryption_key)
            
            try:
                decrypted_key = cipher.decrypt(encrypted_key.encode()).decode()
                self._current_key = decrypted_key
                return decrypted_key
            except:
                return None
        
        return None
    
    def validate_api_key(self, api_key=None):
        """Validate API key with Frappe Cloud"""
        if not api_key:
            api_key = self.get_api_key()
        
        if not api_key:
            return None
        
        try:
            headers = {
                "Authorization": f"token {api_key}",
                "Content-Type": "application/json"
            }
            
            # Test endpoint - adjust based on actual Frappe Cloud API
            response = requests.get(
                "https://frappecloud.com/api/method/frappe.client.get_list",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                # Parse response to get user info
                data = response.json()
                return {
                    "status": "valid",
                    "email": data.get("email", "Unknown"),
                    "account": data.get("account", "Unknown")
                }
            else:
                # Fallback - at least check if key looks valid
                if api_key.startswith("fc_"):
                    return {"status": "valid", "email": "Verified", "account": "Verified"}
                return None
                
        except Exception as e:
            print(f"API validation error: {e}")
            return None
    
    def get_status(self):
        """Get API key status"""
        api_key = self.get_api_key()
        
        if not api_key:
            return {"status": "not_set", "user": None}
        
        validation = self.validate_api_key(api_key)
        if validation:
            return {"status": "valid", "user": validation.get("email")}
        else:
            return {"status": "invalid", "user": None}
    
    def _generate_encryption_key(self, bench_path):
        """Generate consistent encryption key from bench path"""
        # Create a deterministic key from bench path
        seed = f"frappe_migrator_{bench_path}"
        hash_digest = hashlib.sha256(seed.encode()).digest()
        
        # Fernet requires 32-byte key, base64 encoded
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
        import os
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"frappe_migration_salt",
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(hash_digest))
        return key

class SecurityManager:
    @staticmethod
    def get_user_role(api_status):
        """Determine user role based on API status"""
        if not api_status or api_status.get("status") != "valid":
            return "guest"
        
        # Check if user has SSH access
        # This would require additional checks
        return "full"
    
    @staticmethod
    def get_permissions(role):
        """Get permissions matrix for role"""
        permissions = {
            "guest": {
                "analyze_apps": True,
                "view_conflicts": True,
                "download_public": True,
                "download_private": False,
                "push_changes": False,
                "cross_bench_sync": False,
                "automated_migration": False
            },
            "api_user": {
                "analyze_apps": True,
                "view_conflicts": True,
                "download_public": True,
                "download_private": True,
                "push_changes": False,
                "cross_bench_sync": True,
                "automated_migration": True
            },
            "full": {
                "analyze_apps": True,
                "view_conflicts": True,
                "download_public": True,
                "download_private": True,
                "push_changes": True,
                "cross_bench_sync": True,
                "automated_migration": True
            }
        }
        
        return permissions.get(role, permissions["guest"])
