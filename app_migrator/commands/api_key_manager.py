"""
API Key Manager for Frappe Cloud - Secure session-based API key management
"""

import base64
import getpass
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import click
import keyring


class APISessionManager:
    """Secure API session manager with multiple storage options"""

    SESSION_FILE = ".frappe_cloud_session"
    SERVICE_NAME = "frappe_cloud_app_migrator"

    def __init__(self, bench_path: Path | None = None):
        self.bench_path = bench_path or Path(os.getenv('BENCH_PATH', '/home/frappe/frappe-bench'))
        self.session_file = self.bench_path / self.SESSION_FILE

    def _hash_key(self, api_key: str) -> str:
        """Create a secure hash of the API key for verification"""
        salt = os.urandom(16)
        key_hash = hashlib.pbkdf2_hmac('sha256', api_key.encode(), salt, 100000)
        return base64.b64encode(salt + key_hash).decode()

    def _verify_key(self, api_key: str, stored_hash: str) -> bool:
        """Verify an API key against stored hash"""
        try:
            decoded = base64.b64decode(stored_hash)
            salt = decoded[:16]
            stored_key_hash = decoded[16:]
            key_hash = hashlib.pbkdf2_hmac('sha256', api_key.encode(), salt, 100000)
            return key_hash == stored_key_hash
        except Exception:
            return False

    def prompt_for_api_key(self) -> str | None:
        """Securely prompt for API key with options"""
        click.echo("\n🔑 Frappe Cloud API Key Setup")
        click.echo("=" * 30)
        click.echo("\nOptions:")
        click.echo("1. 🔐 Enter API key securely (recommended)")
        click.echo("2. 📝 Enter API key visible (for testing)")
        click.echo("3. 🚪 Skip - Use without API key")

        choice = click.prompt("\nChoose option (1-3)", type=int, default=1)

        if choice == 3:
            return None

        if choice == 1:
            # Secure input
            api_key = getpass.getpass("Enter Frappe Cloud API key: ")
            confirm_key = getpass.getpass("Confirm API key: ")

            if api_key != confirm_key:
                click.echo("❌ API keys don't match!")
                return None

            if not api_key.strip():
                click.echo("❌ API key cannot be empty!")
                return None

            return api_key.strip()

        elif choice == 2:
            # Visible input (for testing/debugging)
            api_key = click.prompt("Enter Frappe Cloud API key", hide_input=False)

            if not api_key.strip():
                click.echo("❌ API key cannot be empty!")
                return None

            return api_key.strip()

        return None

    def save_session(self, api_key: str, keep_secret: bool = False,
                    expiry_hours: int = 24, description: str = "") -> dict[str, Any]:
        """Save API session with security options"""

        session_data = {
            'api_key_hash': self._hash_key(api_key),
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=expiry_hours)).isoformat(),
            'keep_in_keyring': keep_secret,
            'keyring_stored': False,
            'description': description,
            'bench_path': str(self.bench_path)
        }

        # Store in keyring if requested
        if keep_secret:
            try:
                keyring.set_password(self.SERVICE_NAME, "frappe_cloud_api_key", api_key)
                session_data['keyring_stored'] = True
                click.echo("✅ API key securely stored in system keyring")
            except Exception as e:
                click.echo(f"⚠️  Could not store in keyring: {e!s}")
                click.echo("   The key will only be kept in memory for this session")
                session_data['keep_in_keyring'] = False
                # We'll need to keep it in memory temporarily
                session_data['api_key_memory'] = api_key

        # Save session metadata (without actual key)
        try:
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)

            click.echo(f"✅ Session saved (expires: {session_data['expires_at']})")
            return session_data

        except Exception as e:
            click.echo(f"❌ Error saving session: {e!s}")
            return {}

    def load_api_key(self) -> str | None:
        """Load API key from available sources"""

        # 1. Try from environment variable
        env_key = os.getenv('FRAPPE_CLOUD_API_KEY')
        if env_key:
            click.echo("📝 Using API key from environment variable")
            return env_key

        # 2. Try from session file
        if self.session_file.exists():
            try:
                with open(self.session_file) as f:
                    session_data = json.load(f)

                # Check expiry
                expires_at = datetime.fromisoformat(session_data['expires_at'])
                if datetime.now() > expires_at:
                    click.echo("⚠️  Session expired")
                    if click.confirm("Clear expired session?", default=True):
                        self.clear_session()
                    return None

                # Try to get from keyring
                if session_data.get('keyring_stored'):
                    try:
                        api_key = keyring.get_password(self.SERVICE_NAME, "frappe_cloud_api_key")
                        if api_key and self._verify_key(api_key, session_data['api_key_hash']):
                            hours_left = (expires_at - datetime.now()).total_seconds() / 3600
                            click.echo(f"✅ Loaded API key from keyring ({hours_left:.1f}h remaining)")
                            return api_key
                        else:
                            click.echo("⚠️  Keyring key verification failed")
                    except Exception as e:
                        click.echo(f"⚠️  Could not read from keyring: {e!s}")

                # Check for in-memory key (only for current session)
                if 'api_key_memory' in session_data:
                    api_key = session_data['api_key_memory']
                    if self._verify_key(api_key, session_data['api_key_hash']):
                        click.echo("⚠️  Using in-memory API key (not stored securely)")
                        click.echo("   Use --keep-secret to store securely next time")
                        return api_key

                return None

            except Exception as e:
                click.echo(f"⚠️  Error loading session: {e!s}")
                return None

        return None

    def clear_session(self, clear_keyring: bool = True) -> bool:
        """Clear session data"""
        try:
            # Remove session file
            if self.session_file.exists():
                self.session_file.unlink()
                click.echo("✅ Session file removed")

            # Remove from keyring
            if clear_keyring:
                try:
                    keyring.delete_password(self.SERVICE_NAME, "frappe_cloud_api_key")
                    click.echo("✅ API key removed from keyring")
                except keyring.errors.PasswordDeleteError:
                    click.echo("ℹ️  No API key found in keyring")
                except Exception as e:
                    click.echo(f"⚠️  Error clearing keyring: {e!s}")

            # Clear environment variable for this process
            if 'FRAPPE_CLOUD_API_KEY' in os.environ:
                del os.environ['FRAPPE_CLOUD_API_KEY']

            return True
        except Exception as e:
            click.echo(f"❌ Error clearing session: {e!s}")
            return False

    def get_session_status(self) -> dict[str, Any]:
        """Get current session status"""
        status = {
            'has_session': False,
            'is_valid': False,
            'expires_at': None,
            'keyring_stored': False,
            'created_at': None,
            'hours_remaining': 0,
            'description': ''
        }

        if not self.session_file.exists():
            return status

        try:
            with open(self.session_file) as f:
                session_data = json.load(f)

            status.update({
                'has_session': True,
                'keyring_stored': session_data.get('keyring_stored', False),
                'created_at': session_data.get('created_at'),
                'expires_at': session_data.get('expires_at'),
                'description': session_data.get('description', '')
            })

            # Check expiry
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            now = datetime.now()

            if now <= expires_at:
                status['is_valid'] = True
                status['hours_remaining'] = round((expires_at - now).total_seconds() / 3600, 1)
            else:
                status['is_valid'] = False

        except Exception as e:
            click.echo(f"⚠️  Error reading session: {e!s}")

        return status

    def prompt_for_session_cleanup(self) -> bool:
        """Interactive session cleanup prompt"""
        status = self.get_session_status()

        if not status['has_session']:
            click.echo("ℹ️  No active session found")
            return True

        click.echo("\n🧹 Session Cleanup")
        click.echo("=" * 30)

        if status['is_valid']:
            click.echo("📝 Active session found:")
            click.echo(f"   Created: {status['created_at']}")
            click.echo(f"   Expires: {status['expires_at']}")
            click.echo(f"   Hours remaining: {status['hours_remaining']}")
            if status['description']:
                click.echo(f"   Description: {status['description']}")

            if click.confirm("\nDo you want to clear this session?", default=False):
                clear_keyring = click.confirm("Also clear from keyring?", default=True)
                return self.clear_session(clear_keyring)
            else:
                click.echo("Session kept")
                return True
        else:
            click.echo("⚠️  Expired session found")
            if click.confirm("Clear expired session?", default=True):
                clear_keyring = click.confirm("Also clear from keyring?", default=True)
                return self.clear_session(clear_keyring)

        return True


@click.command('api-key-setup')
@click.option('--keep-secret', '-k', is_flag=True, help='Store API key securely in system keyring')
@click.option('--expiry-hours', '-e', default=24, help='Session expiry in hours (default: 24)')
@click.option('--description', '-d', help='Description for this session')
@click.option('--clear', '-c', is_flag=True, help='Clear existing session')
def api_key_setup(keep_secret=False, expiry_hours=24, description="", clear=False):
    """
    Setup Frappe Cloud API Key Session
    
    Securely configure API key for Frappe Cloud integration.
    Options to store in system keyring or keep in memory.
    
    Examples:
        bench app-migrator api-key-setup                     # Interactive setup
        bench app-migrator api-key-setup --keep-secret      # Store in keyring
        bench app-migrator api-key-setup --expiry-hours 48  # 48 hour session
        bench app-migrator api-key-setup --clear            # Clear session
    """
    manager = APISessionManager()

    # Clear session if requested
    if clear:
        if manager.prompt_for_session_cleanup():
            click.echo("✅ Session cleanup completed")
        return

    # Check for existing session
    existing_key = manager.load_api_key()
    if existing_key:
        status = manager.get_session_status()
        if status['is_valid']:
            click.echo(f"✅ Valid session found ({status['hours_remaining']}h remaining)")
            if click.confirm("Setup new session anyway?", default=False):
                # Clear existing
                manager.clear_session()
            else:
                click.echo("Using existing session")
                return

    # Get API key from user
    api_key = manager.prompt_for_api_key()
    if not api_key:
        click.echo("❌ No API key provided")
        return

    # Ask for description if not provided
    if not description:
        description = click.prompt("Session description (optional)", default="", show_default=False)

    # Confirm storage method
    if not keep_secret:
        keep_secret = click.confirm(
            "Store API key securely in system keyring? (recommended)",
            default=True
        )

    # Ask for expiry
    if expiry_hours == 24:
        custom_expiry = click.prompt(
            "Session expiry (hours)",
            type=int,
            default=24,
            show_default=True
        )
        expiry_hours = custom_expiry

    # Save session
    session_data = manager.save_session(
        api_key=api_key,
        keep_secret=keep_secret,
        expiry_hours=expiry_hours,
        description=description
    )

    if session_data:
        click.echo("\n✅ API key setup complete!")
        click.echo(f"📝 Description: {description}")
        click.echo(f"⏰ Expires: {session_data['expires_at']}")
        if session_data.get('keyring_stored'):
            click.echo("🔐 Storage: System keyring (secure)")
        else:
            click.echo("⚠️  Storage: Session file only (less secure)")

        # Ask about environment variable
        if click.confirm("\nSet as environment variable for current terminal?", default=False):
            os.environ['FRAPPE_CLOUD_API_KEY'] = api_key
            click.echo("✅ FRAPPE_CLOUD_API_KEY environment variable set")

        # Final cleanup reminder
        if not session_data.get('keyring_stored'):
            click.echo("\n⚠️  REMINDER: API key is not stored securely")
            click.echo("   Run cleanup when done: bench app-migrator api-key-setup --clear")


@click.command('api-key-status')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
def api_key_status(verbose=False):
    """
    Check Frappe Cloud API Key Status
    
    Show current session status and expiry information.
    
    Examples:
        bench app-migrator api-key-status      # Show status
        bench app-migrator api-key-status -v   # Verbose details
    """
    manager = APISessionManager()
    status = manager.get_session_status()

    click.echo("🔍 Frappe Cloud API Key Status")
    click.echo("=" * 35)

    if not status['has_session']:
        click.echo("📭 No active session found")
        click.echo("\n💡 To setup a session:")
        click.echo("   bench app-migrator api-key-setup")
        return

    # Basic status
    if status['is_valid']:
        click.echo(f"✅ ACTIVE SESSION ({status['hours_remaining']}h remaining)")
    else:
        click.echo("❌ EXPIRED SESSION")

    click.echo(f"📅 Created: {status['created_at']}")
    click.echo(f"⏰ Expires: {status['expires_at']}")

    if status['description']:
        click.echo(f"📝 Description: {status['description']}")

    if status['keyring_stored']:
        click.echo("🔐 Storage: System keyring")
    else:
        click.echo("📄 Storage: Session file")

    # Verbose mode
    if verbose:
        click.echo("\n🔍 DETAILS:")
        click.echo(f"  Bench path: {manager.bench_path}")
        click.echo(f"  Session file: {manager.session_file}")
        click.echo(f"  Keyring service: {manager.SERVICE_NAME}")

        # Test keyring access
        try:
            test_key = keyring.get_password(manager.SERVICE_NAME, "frappe_cloud_api_key")
            if test_key:
                click.echo("  Keyring test: ✅ Accessible")
            else:
                click.echo("  Keyring test: ℹ️  No key found")
        except Exception as e:
            click.echo(f"  Keyring test: ❌ Error: {e!s}")

    # Recommendations
    click.echo("\n💡 COMMANDS:")
    if status['is_valid']:
        click.echo("   bench app-migrator git-info --api-key auto")
        click.echo("   bench app-migrator git-pull --api-key auto")
    else:
        click.echo("   bench app-migrator api-key-setup --clear")
        click.echo("   bench app-migrator api-key-setup (new session)")


@click.command('api-key-cleanup')
@click.option('--force', '-f', is_flag=True, help='Force cleanup without confirmation')
@click.option('--keep-keyring', is_flag=True, help='Keep keyring entry (only remove session file)')
def api_key_cleanup(force=False, keep_keyring=False):
    """
    Cleanup Frappe Cloud API Key Session
    
    Securely remove API key from session and keyring.
    
    Examples:
        bench app-migrator api-key-cleanup      # Interactive cleanup
        bench app-migrator api-key-cleanup -f   # Force cleanup
        bench app-migrator api-key-cleanup --keep-keyring  # Keep in keyring
    """
    manager = APISessionManager()

    if force:
        success = manager.clear_session(clear_keyring=not keep_keyring)
        if success:
            click.echo("✅ Session cleanup completed")
        return

    # Interactive cleanup
    if manager.prompt_for_session_cleanup():
        click.echo("✅ Session cleanup completed")
    else:
        click.echo("❌ Cleanup cancelled")


# Add to commands list
commands = [api_key_setup, api_key_status, api_key_cleanup]
