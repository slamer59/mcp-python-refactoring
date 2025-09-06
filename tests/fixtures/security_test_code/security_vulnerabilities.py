#!/usr/bin/env python3
"""
Test file containing various security vulnerabilities for testing SecurityAnalyzer
This file intentionally contains security issues for testing purposes only.
"""

import hashlib
import os
import pickle
import subprocess
import tempfile
import yaml
from ftplib import FTP
import requests
import ssl


# B105: Hardcoded password string
password = "hardcoded_password123"

# B106: Hardcoded password function argument
def authenticate_user(username, password="admin123"):
    return username == "admin" and password == "admin123"


# B107: Hardcoded password default
class DatabaseConnection:
    def __init__(self, host, user, password="default_password"):
        self.host = host
        self.user = user
        self.password = password


# B303: Use of insecure MD5 hash
def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


# B301: Use of pickle with untrusted data
def deserialize_data(data):
    return pickle.loads(data)


# B602: subprocess with shell=True
def run_command(user_input):
    subprocess.call(f"ls {user_input}", shell=True)


# B608: Possible SQL injection
def get_user_data(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    # This would execute the query...
    return query


# B501: SSL certificate verification disabled
def fetch_data(url):
    return requests.get(url, verify=False)


# B506: Use of yaml.load instead of yaml.safe_load
def load_config(config_data):
    return yaml.load(config_data)


# B402: Use of insecure FTP
def upload_file(filename):
    ftp = FTP('example.com')
    ftp.login('user', 'password')
    ftp.storbinary(f'STOR {filename}', open(filename, 'rb'))


# B108: Hardcoded temporary directory
def create_temp_file():
    return open('/tmp/myfile.txt', 'w')


# B110: Try/except with pass (silently ignoring errors)
def risky_operation():
    try:
        # Some risky operation
        result = 1 / 0
        return result
    except:
        pass


# B201: Flask debug mode enabled (if using Flask)
# app.run(debug=True)  # Would be flagged if Flask was imported


# B103: Set bad file permissions
def create_file_with_bad_permissions():
    filename = "sensitive_file.txt"
    with open(filename, 'w') as f:
        f.write("sensitive data")
    os.chmod(filename, 0o777)  # Too permissive


# B104: Hardcoded bind all interfaces
def start_server():
    host = "0.0.0.0"  # Binds to all interfaces
    port = 8080
    # Would start server...
    return f"Server starting on {host}:{port}"


# B306: Use of insecure temporary file function
def insecure_temp_file():
    return tempfile.mktemp()


# B502: SSL with bad TLS version
def create_ssl_context():
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)  # Insecure TLS version
    return context


# B607: Starting process with partial path
def run_unsafe_command():
    subprocess.call("python", shell=False)  # Should use full path


# Multiple vulnerabilities in one function
def extremely_vulnerable_function(user_data, config_file):
    """This function has multiple security issues for comprehensive testing."""
    
    # Hardcoded secrets
    api_key = "sk-1234567890abcdef"
    db_password = "super_secret_password"
    
    # Insecure deserialization
    user_obj = pickle.loads(user_data)
    
    # SQL injection vulnerability
    query = f"UPDATE users SET data = '{user_obj}' WHERE id = {user_obj.get('id')}"
    
    # Command injection
    subprocess.call(f"backup_user_data.sh {user_obj.get('username')}", shell=True)
    
    # Insecure cryptography
    hashed = hashlib.md5(f"{user_obj}{db_password}".encode()).hexdigest()
    
    # Insecure file handling
    config = yaml.load(open(config_file).read())
    
    # Network security issues
    response = requests.get(config.get('api_url'), verify=False)
    
    # Bad exception handling
    try:
        risky_network_call = requests.get("http://unsafe-site.com")
        return process_response(risky_network_call, hashed)
    except:
        pass
    
    return None


def process_response(response, hash_val):
    """Helper function for the vulnerable function above."""
    return {"status": "processed", "hash": hash_val, "data": response.text}