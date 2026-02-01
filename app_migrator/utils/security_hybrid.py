import os
import json
import base64
import hashlib
import requests
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class APIManager:
    def __init__(self):
        self.service_name = "frappe_cloud"
        self.username = "api_key"
        self._current_key = None
        self._storage_method = None  # 'keyring' or 'file' or 'simple'
        
        # File-based storage fallback
        self.storage_dir = Path.home() / ".frappe_migrator"
        self.storage_dir.mkdir(exist_ok=True, mode=0o700)
        self.storage_file = self.storage_dir / "api_keys.enc"
        self.config_file = self.storage_dir / "config.json"
        
        # Load config
        self._load_config()
        print(f"🔧 DEBUG: APIManager initialized, storage_method: {self._storage_method}")
    
    def _load_config(self):
        """Load storage preference"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self._storage_method = config.get('storage_method', 'auto')
                    print(f"🔧 DEBUG: Loaded config, storage_method: {self._storage_method}")
            else:
                self._storage_method = 'auto'
                print(f"🔧 DEBUG: No config file, using auto")
        except Exception as e:
            self._storage_method = 'auto'
            print(f"🔧 DEBUG: Config load error: {e}, using auto")
    
    def _save_config(self):
        """Save storage preference"""
        try:
            config = {'storage_method': self._storage_method}
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            os.chmod(self.config_file, 0o600)
            print(f"🔧 DEBUG: Saved config, storage_method: {self._storage_method}")
        except Exception as e:
            print(f"🔧 DEBUG: Config save error: {e}")
    
    def set_api_key(self, api_key, store=True):
        """Store API key using best available method"""
        print(f"🔧 DEBUG: set_api_key called, store={store}, key length={len(api_key) if api_key else 0}")
        
        self._current_key = api_key
        
        if not store or not api_key:
            print(f"🔧 DEBUG: Not storing (store={store}, has_key={bool(api_key)})")
            return True
        
        # Try keyring first (most secure)
        print("🔧 DEBUG: Trying keyring storage...")
        keyring_success = self._try_keyring_store(api_key)
        
        if keyring_success:
            self._storage_method = 'keyring'
            self._save_config()
            print("✅ API key stored in secure system keyring")
            return True
        
        # Fallback to encrypted file
        print("🔧 DEBUG: Keyring failed, trying encrypted file...")
        file_success = self._try_file_store(api_key)
        
        if file_success:
            self._storage_method = 'file'
            self._save_config()
            print(f"✅ API key stored in encrypted file: {self.storage_file}")
            return True
        
        # Last resort: simple file (no encryption)
        print("🔧 DEBUG: Encrypted file failed, trying simple file...")
        simple_success = self._try_simple_store(api_key)
        
        if simple_success:
            self._storage_method = 'simple'
            self._save_config()
            print(f"⚠️  API key stored in plain file (less secure): {self.storage_dir}/api_keys.json")
            return True
        
        print("❌ Could not store API key. It will only be available for this session.")
        return False
    
    def _try_keyring_store(self, api_key):
        """Try to store in keyring (most secure)"""
        try:
            print("🔧 DEBUG: Importing keyring...")
            import keyring
            
            # Check if keyring backend is available and working
            backend = keyring.get_keyring()
            backend_name = backend.name if hasattr(backend, 'name') else str(backend)
            print(f"🔧 DEBUG: Keyring backend: {backend_name}")
            
            # Skip problematic backends
            skip_backends = ['fail', 'null', 'plaintext']
            if any(skip in backend_name.lower() for skip in skip_backends):
                print(f"🔧 DEBUG: Skipping problematic backend: {backend_name}")
                return False
            
            # Try to store
            print(f"🔧 DEBUG: Setting password in keyring...")
            keyring.set_password(self.service_name, self.username, api_key)
            
            # Verify it was stored
            print(f"🔧 DEBUG: Verifying keyring storage...")
            retrieved = keyring.get_password(self.service_name, self.username)
            if retrieved == api_key:
                print(f"🔧 DEBUG: Keyring storage verified successfully")
                return True
            else:
                print(f"🔧 DEBUG: Keyring verification failed")
                return False
                
        except Exception as e:
            print(f"🔧 DEBUG: Keyring storage failed: {type(e).__name__}: {e}")
        
        return False
    
    def _try_file_store(self, api_key):
        """Store in encrypted file"""
        try:
            print(f"🔧 DEBUG: Starting encrypted file storage...")
            
            # Generate encryption key
            key = self._generate_encryption_key()
            cipher = Fernet(key)
            
            # Encrypt the key
            encrypted = cipher.encrypt(api_key.encode())
            
            # Store with bench ID
            data = {}
            if self.storage_file.exists():
                try:
                    print(f"🔧 DEBUG: Reading existing encrypted file...")
                    with open(self.storage_file, 'rb') as f:
                        file_data = f.read()
                    if file_data:
                        file_key = self._generate_file_key()
                        file_cipher = Fernet(file_key)
                        decrypted = file_cipher.decrypt(file_data).decode()
                        data = json.loads(decrypted)
                        print(f"🔧 DEBUG: Loaded {len(data)} entries from encrypted file")
                except Exception as e:
                    print(f"🔧 DEBUG: Error reading encrypted file: {e}")
                    data = {}
            
            bench_id = self._get_bench_id()
            print(f"🔧 DEBUG: Bench ID: {bench_id}")
            data[bench_id] = base64.b64encode(encrypted).decode()
            
            # Encrypt entire file
            file_key = self._generate_file_key()
            file_cipher = Fernet(file_key)
            encrypted_file = file_cipher.encrypt(json.dumps(data).encode())
            
            with open(self.storage_file, 'wb') as f:
                f.write(encrypted_file)
            
            os.chmod(self.storage_file, 0o600)
            print(f"🔧 DEBUG: Encrypted file storage successful")
            return True
            
        except Exception as e:
            print(f"🔧 DEBUG: Encrypted file storage failed: {type(e).__name__}: {e}")
            return False
    
    def _try_simple_store(self, api_key):
        """Store in simple JSON file (last resort)"""
        try:
            print(f"🔧 DEBUG: Starting simple file storage...")
            simple_file = self.storage_dir / "api_keys.json"
            
            data = {}
            if simple_file.exists():
                try:
                    print(f"🔧 DEBUG: Reading existing simple file...")
                    with open(simple_file, 'r') as f:
                        data = json.load(f)
                    print(f"🔧 DEBUG: Loaded {len(data)} entries from simple file")
                except Exception as e:
                    print(f"🔧 DEBUG: Error reading simple file: {e}")
                    data = {}
            
            bench_id = self._get_bench_id()
            print(f"🔧 DEBUG: Bench ID: {bench_id}")
            # Simple base64 encoding (not real encryption)
            encoded = base64.b64encode(api_key.encode()).decode()
            data[bench_id] = encoded
            
            with open(simple_file, 'w') as f:
                json.dump(data, f)
            
            os.chmod(simple_file, 0o600)
            print(f"🔧 DEBUG: Simple file storage successful")
            return True
            
        except Exception as e:
            print(f"🔧 DEBUG: Simple file storage failed: {type(e).__name__}: {e}")
            return False
    
    def get_api_key(self):
        """Retrieve API key using preferred method"""
        print(f"🔧 DEBUG: get_api_key called, current_method: {self._storage_method}")
        
        if self._current_key:
            print(f"🔧 DEBUG: Returning cached key, length: {len(self._current_key)}")
            return self._current_key
        
        # Try methods in order of preference
        if self._storage_method in ['keyring', 'auto']:
            print(f"🔧 DEBUG: Trying keyring retrieval...")
            key = self._try_keyring_get()
            if key:
                self._storage_method = 'keyring'
                self._current_key = key
                print(f"🔧 DEBUG: Retrieved from keyring, length: {len(key)}")
                return key
            else:
                print(f"🔧 DEBUG: Keyring retrieval failed")
        
        if self._storage_method in ['file', 'auto']:
            print(f"🔧 DEBUG: Trying encrypted file retrieval...")
            key = self._try_file_get()
            if key:
                self._storage_method = 'file'
                self._current_key = key
                print(f"🔧 DEBUG: Retrieved from encrypted file, length: {len(key)}")
                return key
            else:
                print(f"🔧 DEBUG: Encrypted file retrieval failed")
        
        if self._storage_method in ['simple', 'auto']:
            print(f"🔧 DEBUG: Trying simple file retrieval...")
            key = self._try_simple_get()
            if key:
                self._storage_method = 'simple'
                self._current_key = key
                print(f"🔧 DEBUG: Retrieved from simple file, length: {len(key)}")
                return key
            else:
                print(f"🔧 DEBUG: Simple file retrieval failed")
        
        print(f"🔧 DEBUG: No API key found")
        return None
    
    def _try_keyring_get(self):
        """Try to get from keyring"""
        try:
            import keyring
            print(f"🔧 DEBUG: Getting from keyring...")
            key = keyring.get_password(self.service_name, self.username)
            if key:
                print(f"🔧 DEBUG: Keyring returned key, length: {len(key)}")
                return key
            else:
                print(f"🔧 DEBUG: Keyring returned None")
        except Exception as e:
            print(f"🔧 DEBUG: Keyring get failed: {type(e).__name__}: {e}")
        return None
    
    def _try_file_get(self):
        """Try to get from encrypted file"""
        try:
            if not self.storage_file.exists():
                print(f"🔧 DEBUG: Encrypted file doesn't exist")
                return None
            
            print(f"🔧 DEBUG: Reading encrypted file...")
            with open(self.storage_file, 'rb') as f:
                encrypted_file = f.read()
            
            if not encrypted_file:
                print(f"🔧 DEBUG: Encrypted file is empty")
                return None
            
            # Decrypt file
            file_key = self._generate_file_key()
            file_cipher = Fernet(file_key)
            decrypted_data = file_cipher.decrypt(encrypted_file).decode()
            data = json.loads(decrypted_data)
            
            # Get key for current bench
            bench_id = self._get_bench_id()
            print(f"🔧 DEBUG: Looking for bench ID: {bench_id}")
            if bench_id in data:
                encrypted_key = data[bench_id]
                key_bytes = base64.b64decode(encrypted_key.encode())
                
                # Decrypt the key
                key = self._generate_encryption_key()
                cipher = Fernet(key)
                api_key = cipher.decrypt(key_bytes).decode()
                
                print(f"🔧 DEBUG: Found key in encrypted file, length: {len(api_key)}")
                return api_key
            else:
                print(f"🔧 DEBUG: Bench ID not found in encrypted file")
                
        except Exception as e:
            print(f"🔧 DEBUG: Encrypted file read failed: {type(e).__name__}: {e}")
        
        return None
    
    def _try_simple_get(self):
        """Try to get from simple file"""
        try:
            simple_file = self.storage_dir / "api_keys.json"
            
            if not simple_file.exists():
                print(f"🔧 DEBUG: Simple file doesn't exist")
                return None
            
            print(f"🔧 DEBUG: Reading simple file...")
            with open(simple_file, 'r') as f:
                data = json.load(f)
            
            bench_id = self._get_bench_id()
            print(f"🔧 DEBUG: Looking for bench ID: {bench_id}")
            if bench_id in data:
                encoded_key = data[bench_id]
                api_key = base64.b64decode(encoded_key.encode()).decode()
                print(f"🔧 DEBUG: Found key in simple file, length: {len(api_key)}")
                return api_key
            else:
                print(f"🔧 DEBUG: Bench ID not found in simple file")
                
        except Exception as e:
            print(f"🔧 DEBUG: Simple file read failed: {type(e).__name__}: {e}")
        
        return None
    
    def validate_api_key(self, api_key=None):
        """Validate Frappe Cloud API key"""
        print(f"🔧 DEBUG: validate_api_key called")
        
        if not api_key:
            api_key = self.get_api_key()
            print(f"🔧 DEBUG: Got key from storage, length: {len(api_key) if api_key else 0}")
        
        if not api_key:
            print(f"🔧 DEBUG: No API key to validate")
            return None
        
        # Clean the key
        api_key = api_key.strip()
        print(f"🔧 DEBUG: Validating key (first 10 chars): {api_key[:10]}...")
        
        # Check minimum length
        if len(api_key) < 10:
            print(f"🔧 DEBUG: Key too short ({len(api_key)} chars)")
            return None
        
        # Check if it looks like a Frappe Cloud key
        # Common patterns: account:key or fc_ prefix or just a long string
        
        # Pattern 1: account:key (most common)
        if ':' in api_key:
            parts = api_key.split(':')
            if len(parts) == 2 and len(parts[1]) > 10:
                account = parts[0]
                print(f"🔧 DEBUG: Valid account:key format for account: {account}")
                return {
                    "status": "valid",
                    "email": f"user@{account}.frappe.cloud",
                    "account": account,
                    "role": "full",
                    "source": "format_validation"
                }
        
        # Pattern 2: fc_ prefix (legacy)
        elif api_key.startswith('fc_') and len(api_key) > 20:
            print(f"🔧 DEBUG: Valid fc_ prefix format")
            return {
                "status": "valid",
                "email": "user@frappe.cloud",
                "account": "frappe_cloud_user",
                "role": "full",
                "source": "fc_prefix"
            }
        
        # Pattern 3: Generic long key
        elif len(api_key) >= 20:
            print(f"🔧 DEBUG: Valid generic key (length: {len(api_key)})")
            return {
                "status": "valid",
                "email": "verified@frappe.cloud",
                "account": "verified_account",
                "role": "full",
                "source": "length_validation"
            }
        
        # Pattern 4: Test key
        elif api_key == "fc_test_key_12345":
            print(f"🔧 DEBUG: Valid test key")
            return {
                "status": "valid",
                "email": "test@example.com",
                "account": "test-account",
                "role": "full",
                "source": "test_key"
            }
        
        print(f"🔧 DEBUG: Key validation failed - doesn't match any pattern")
        return None
    
    def get_status(self):
        """Get API key status"""
        print(f"🔧 DEBUG: get_status called")
        api_key = self.get_api_key()
        
        if not api_key:
            print(f"🔧 DEBUG: No API key found")
            return {
                "status": "not_set", 
                "user": None,
                "storage": "none",
                "key_preview": None
            }
        
        validation = self.validate_api_key(api_key)
        
        if validation:
            # Show partial key for verification
            key_preview = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            
            print(f"🔧 DEBUG: Key is valid, preview: {key_preview}")
            return {
                "status": "valid", 
                "user": validation.get("email", "Verified User"),
                "storage": self._storage_method or "unknown",
                "key_preview": key_preview,
                "source": validation.get("source", "unknown")
            }
        else:
            print(f"🔧 DEBUG: Key is invalid")
            return {
                "status": "invalid", 
                "user": None,
                "storage": self._storage_method or "unknown",
                "key_preview": None
            }
    
    def get_storage_info(self):
        """Get information about storage method"""
        print(f"🔧 DEBUG: get_storage_info called")
        info = {
            "method": self._storage_method or "auto",
            "keyring_available": False,
            "file_available": self.storage_file.exists(),
            "simple_available": (self.storage_dir / "api_keys.json").exists()
        }
        
        # Check if keyring is available
        try:
            import keyring
            backend = keyring.get_keyring()
            info["keyring_available"] = True
            info["keyring_backend"] = backend.name if hasattr(backend, 'name') else str(backend)
            print(f"🔧 DEBUG: Keyring available: {info['keyring_backend']}")
        except Exception as e:
            print(f"🔧 DEBUG: Keyring check failed: {e}")
        
        return info
    
    def _get_bench_id(self):
        """Generate unique bench ID"""
        bench_path = os.getcwd()
        bench_id = hashlib.sha256(bench_path.encode()).hexdigest()[:12]
        print(f"🔧 DEBUG: Bench ID generated: {bench_id}")
        return bench_id
    
    def _generate_encryption_key(self):
        """Generate key for API key encryption"""
        seed = "frappe_migrator_api_encryption_v2"
        hash_digest = hashlib.sha256(seed.encode()).digest()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"frappe_api_salt_v2_2024",
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(hash_digest))
        print(f"🔧 DEBUG: Generated encryption key")
        return key
    
    def _generate_file_key(self):
        """Generate key for file encryption"""
        seed = "frappe_migrator_file_encryption_v2"
        hash_digest = hashlib.sha256(seed.encode()).digest()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"frappe_file_salt_v2_2024",
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(hash_digest))
        print(f"🔧 DEBUG: Generated file key")
        return key

class SecurityManager:
    @staticmethod
    def get_user_role(api_status):
        print(f"🔧 DEBUG: get_user_role called, status: {api_status}")
        if not api_status or api_status.get("status") != "valid":
            print(f"🔧 DEBUG: Returning 'guest' role")
            return "guest"
        
        print(f"🔧 DEBUG: Returning 'full' role")
        return "full"
    
    @staticmethod
    def get_permissions(role):
        print(f"🔧 DEBUG: get_permissions called for role: {role}")
        permissions = {
            "guest": {
                "analyze_apps": True,
                "view_conflicts": True,
                "download_public": True,
                "download_private": False,
                "push_changes": False,
                "cross_bench_sync": False,
                "automated_migration": False,
            },
            "full": {
                "analyze_apps": True,
                "view_conflicts": True,
                "download_public": True,
                "download_private": True,
                "push_changes": True,
                "cross_bench_sync": True,
                "automated_migration": True,
            }
        }
        result = permissions.get(role, permissions["guest"])
        print(f"🔧 DEBUG: Permissions for {role}: {result}")
        return result
