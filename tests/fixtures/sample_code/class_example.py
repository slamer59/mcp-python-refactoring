# Class with multiple methods for testing class-level analysis

class UserManager:
    """Manages user accounts and operations."""
    
    def __init__(self):
        self.users = {}
        self.active_sessions = {}
        self.settings = {
            'max_login_attempts': 3,
            'session_timeout': 3600,
            'password_min_length': 8
        }
    
    def create_user(self, username, email, password):
        """Create a new user account."""
        if not username or len(username.strip()) < 3:
            raise ValueError("Username must be at least 3 characters")
        
        if not email or "@" not in email:
            raise ValueError("Invalid email address")
        
        if not password or len(password) < self.settings['password_min_length']:
            raise ValueError(f"Password must be at least {self.settings['password_min_length']} characters")
        
        if username in self.users:
            raise ValueError("Username already exists")
        
        user_data = {
            'username': username.strip(),
            'email': email.strip().lower(),
            'password_hash': self._hash_password(password),
            'created_at': 'timestamp_here',
            'login_attempts': 0,
            'is_active': True
        }
        
        self.users[username] = user_data
        return user_data
    
    def authenticate_user(self, username, password):
        """Authenticate a user login attempt."""
        if username not in self.users:
            return False
        
        user = self.users[username]
        
        if not user['is_active']:
            return False
        
        if user['login_attempts'] >= self.settings['max_login_attempts']:
            return False
        
        if self._verify_password(password, user['password_hash']):
            user['login_attempts'] = 0
            return True
        else:
            user['login_attempts'] += 1
            return False
    
    def create_session(self, username):
        """Create a new user session."""
        if username not in self.users:
            raise ValueError("User not found")
        
        session_id = f"session_{username}_{len(self.active_sessions)}"
        session_data = {
            'username': username,
            'created_at': 'timestamp_here',
            'expires_at': 'timestamp_plus_timeout_here',
            'is_active': True
        }
        
        self.active_sessions[session_id] = session_data
        return session_id
    
    def validate_session(self, session_id):
        """Validate if a session is still active."""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        return session['is_active']
    
    def deactivate_user(self, username):
        """Deactivate a user account."""
        if username in self.users:
            self.users[username]['is_active'] = False
            
            # Remove all active sessions for this user
            sessions_to_remove = [
                session_id for session_id, session in self.active_sessions.items()
                if session['username'] == username
            ]
            
            for session_id in sessions_to_remove:
                del self.active_sessions[session_id]
            
            return True
        return False
    
    def _hash_password(self, password):
        """Hash a password (simplified for testing)."""
        return f"hashed_{password}"
    
    def _verify_password(self, password, password_hash):
        """Verify a password against its hash."""
        return f"hashed_{password}" == password_hash