#!/usr/bin/env python3
"""
Test file with clean, modern Python code that should have minimal security/modernization issues.
This serves as a control test to ensure analyzers don't produce false positives.
"""

import hashlib
import logging
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union
import requests
import yaml
import ssl


# Configure logging properly
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecureUserManager:
    """A modern, secure user management class following best practices."""
    
    def __init__(self, db_path: Path, api_config: Dict[str, str]):
        self.db_path = Path(db_path)
        self.api_config = api_config
        self._ensure_db_exists()
    
    def _ensure_db_exists(self) -> None:
        """Create database if it doesn't exist."""
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._create_tables()
    
    def _create_tables(self) -> None:
        """Create necessary database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def hash_password(self, password: str) -> str:
        """Securely hash a password using bcrypt-equivalent approach."""
        # Using SHA-256 with salt for this example (in production, use bcrypt)
        import secrets
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${password_hash}"
    
    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify a password against stored hash."""
        try:
            salt, hash_part = stored_hash.split('$')
            computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return hash_part == computed_hash
        except ValueError:
            logger.error("Invalid hash format")
            return False
    
    def create_user(self, username: str, email: str, password: str) -> Optional[int]:
        """Create a new user with proper validation and security."""
        if not self._validate_username(username):
            logger.warning(f"Invalid username: {username}")
            return None
        
        if not self._validate_email(email):
            logger.warning(f"Invalid email: {email}")
            return None
        
        password_hash = self.hash_password(password)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, password_hash)
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.error(f"User {username} or {email} already exists")
            return None
    
    def get_user(self, username: str) -> Optional[Dict[str, Union[str, int]]]:
        """Get user information by username using parameterized query."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, username, email, created_at FROM users WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def _validate_username(self, username: str) -> bool:
        """Validate username format."""
        return (isinstance(username, str) and 
                3 <= len(username) <= 50 and 
                username.isalnum())
    
    def _validate_email(self, email: str) -> bool:
        """Basic email validation."""
        return isinstance(email, str) and '@' in email and len(email) <= 255


class SecureFileProcessor:
    """Modern file processing with security best practices."""
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def process_files(self, file_patterns: List[str]) -> Dict[str, List[str]]:
        """Process files using modern Python patterns."""
        results = {}
        
        for pattern in file_patterns:
            matching_files = list(self.base_path.glob(pattern))
            
            # Use list comprehension for filtering
            valid_files = [f for f in matching_files if f.is_file() and f.suffix == '.txt']
            
            # Use enumerate for indexed iteration
            processed_content = []
            for idx, file_path in enumerate(valid_files):
                content = self._read_file_safely(file_path)
                processed_content.append(f"File {idx}: {content[:100]}...")
            
            results[pattern] = processed_content
        
        return results
    
    def _read_file_safely(self, file_path: Path) -> str:
        """Read file with proper error handling and context manager."""
        try:
            with file_path.open('r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return ""
        except PermissionError:
            logger.error(f"Permission denied: {file_path}")
            return ""
        except UnicodeDecodeError:
            logger.error(f"Encoding error: {file_path}")
            return ""
    
    def create_secure_temp_file(self, content: str) -> Optional[Path]:
        """Create temporary file with proper security."""
        import tempfile
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, 
                                           dir=self.base_path, suffix='.tmp') as f:
                f.write(content)
                temp_path = Path(f.name)
            
            # Set restrictive permissions (owner read/write only)
            temp_path.chmod(0o600)
            return temp_path
        
        except OSError as e:
            logger.error(f"Failed to create temporary file: {e}")
            return None


class SecureConfigManager:
    """Secure configuration management with modern patterns."""
    
    def __init__(self, config_path: Path):
        self.config_path = Path(config_path)
    
    def load_config(self) -> Dict[str, any]:
        """Load configuration safely."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            return {}
        
        try:
            with self.config_path.open('r') as f:
                # Use safe_load to prevent arbitrary code execution
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in config: {e}")
            return {}
    
    def save_config(self, config_data: Dict[str, any]) -> bool:
        """Save configuration securely."""
        try:
            # Create backup first
            backup_path = self.config_path.with_suffix('.backup')
            if self.config_path.exists():
                self.config_path.rename(backup_path)
            
            with self.config_path.open('w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            
            # Set appropriate permissions
            self.config_path.chmod(0o644)
            return True
            
        except (OSError, yaml.YAMLError) as e:
            logger.error(f"Failed to save config: {e}")
            # Restore backup if it exists
            backup_path = self.config_path.with_suffix('.backup')
            if backup_path.exists():
                backup_path.rename(self.config_path)
            return False


class SecureNetworkClient:
    """Network client with proper security practices."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
        # Create secure SSL context
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = True
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED
    
    def make_secure_request(self, endpoint: str, 
                          data: Optional[Dict] = None) -> Optional[Dict]:
        """Make a secure HTTP request with proper validation."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if data:
                response = self.session.post(url, json=data, 
                                           timeout=self.timeout, verify=True)
            else:
                response = self.session.get(url, timeout=self.timeout, verify=True)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL verification failed: {e}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def close(self) -> None:
        """Clean up resources."""
        self.session.close()


def secure_data_processing(data_list: List[Dict[str, any]]) -> Dict[str, any]:
    """Process data using modern Python patterns and secure practices."""
    if not data_list:
        return {"error": "No data provided"}
    
    # Use any() instead of loop for existence check
    has_valid_items = any(item.get('valid', False) for item in data_list)
    
    # Use all() for validation check
    all_have_ids = all('id' in item for item in data_list)
    
    # Use dict comprehension for mapping
    id_to_data = {item['id']: item for item in data_list if 'id' in item}
    
    # Use list comprehension with filtering
    active_items = [item for item in data_list if item.get('status') == 'active']
    
    # Use enumerate for indexed processing
    indexed_results = [
        f"Item {idx}: {item.get('name', 'Unknown')}" 
        for idx, item in enumerate(data_list)
    ]
    
    # Use next() to find first match
    first_admin = next(
        (item for item in data_list if item.get('role') == 'admin'), 
        None
    )
    
    # Use zip() for parallel processing
    names = [item.get('name', '') for item in data_list]
    statuses = [item.get('status', '') for item in data_list]
    combined_info = list(zip(names, statuses))
    
    # Use f-strings for formatting
    summary = f"Processed {len(data_list)} items, {len(active_items)} active"
    
    return {
        "summary": summary,
        "has_valid_items": has_valid_items,
        "all_have_ids": all_have_ids,
        "active_count": len(active_items),
        "first_admin": first_admin,
        "combined_info": combined_info,
        "indexed_results": indexed_results
    }


def run_secure_subprocess(command_args: List[str], cwd: Optional[Path] = None) -> bool:
    """Run subprocess securely without shell injection risks."""
    if not command_args:
        logger.error("No command provided")
        return False
    
    # Validate that we have an absolute path for the executable
    executable = Path(command_args[0])
    if not executable.is_absolute():
        logger.error(f"Executable must be absolute path: {command_args[0]}")
        return False
    
    try:
        # Use shell=False to prevent injection attacks
        result = subprocess.run(
            command_args,
            cwd=cwd,
            shell=False,  # Explicitly disable shell
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info("Command executed successfully")
            return True
        else:
            logger.error(f"Command failed with code {result.returncode}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Command timed out")
        return False
    except FileNotFoundError:
        logger.error(f"Executable not found: {command_args[0]}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


# Example usage with proper patterns
if __name__ == "__main__":
    # Use pathlib for path operations
    base_dir = Path(__file__).parent
    
    # Use context managers and proper resource management
    with SecureNetworkClient("https://api.example.com") as client:
        # Modern, secure operations...
        pass