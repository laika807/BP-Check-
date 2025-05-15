import sqlite3
import hashlib
import datetime
import os
import secrets
import time
from datetime import datetime, timedelta

# Try to import JWT - if not available, use a fallback implementation
try:
    import jwt
    HAS_JWT = True
except ImportError:
    print("PyJWT package not found. Using fallback implementation.")
    HAS_JWT = False
    
    # Define error classes to match JWT's
    class ExpiredSignatureError(Exception): pass
    class InvalidTokenError(Exception): pass
    
    # Basic JWT fallback (for dev only - not secure for production)
    class FallbackJWT:
        # Add error classes as attributes
        ExpiredSignatureError = ExpiredSignatureError
        InvalidTokenError = InvalidTokenError
        
        @staticmethod
        def encode(payload, secret, algorithm=None):
            """Simple fallback that base64 encodes the payload with a timestamp"""
            import base64
            import json
            
            # Add timestamp to payload
            payload_copy = payload.copy()
            payload_copy['iat'] = int(time.time())
            
            # Encode payload as JSON and then base64
            payload_json = json.dumps(payload_copy)
            token = base64.b64encode(payload_json.encode()).decode()
            
            # Add a simple signature using the secret
            signature = hashlib.sha256((token + secret).encode()).hexdigest()
            
            return f"{token}.{signature}"
        
        @staticmethod
        def decode(token, secret, algorithms=None):
            """Decode our simple token format"""
            import base64
            import json
            
            try:
                # Split token and signature
                token_part, signature = token.split('.')
                
                # Verify signature
                expected_sig = hashlib.sha256((token_part + secret).encode()).hexdigest()
                if signature != expected_sig:
                    raise InvalidTokenError("Invalid token")
                
                # Decode payload
                payload_json = base64.b64decode(token_part).decode()
                payload = json.loads(payload_json)
                
                # Check expiry if present
                if 'exp' in payload and payload['exp'] < time.time():
                    raise ExpiredSignatureError("Token expired")
                
                return payload
            except ExpiredSignatureError:
                raise
            except Exception:
                raise InvalidTokenError("Invalid token")
    
    # Use our fallback
    jwt = FallbackJWT()

# Database setup for authentication
AUTH_DB_FILE = "auth.db"

def setup_auth_database():
    """Create authentication database tables if they don't exist"""
    try:
        conn = sqlite3.connect(AUTH_DB_FILE)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            mobile TEXT,
            is_email_verified BOOLEAN DEFAULT 0,
            is_mobile_verified BOOLEAN DEFAULT 0,
            verification_code TEXT,
            verification_code_expiry TIMESTAMP,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create sessions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        ''')
        
        # Create login_attempts table to prevent brute force
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            email TEXT,
            ip_address TEXT NOT NULL,
            attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN
        )
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Auth database setup error: {e}")
        return False

# Ensure database is setup
setup_auth_database()

def generate_salt():
    """Generate a random salt for password hashing"""
    return secrets.token_hex(16)

def hash_password(password, salt):
    """Hash a password with the given salt using SHA-256"""
    password_salt = password + salt
    h = hashlib.sha256()
    h.update(password_salt.encode('utf-8'))
    return h.hexdigest()

def register_user(username, email, password, mobile=None):
    """Register a new user"""
    try:
        conn = sqlite3.connect(AUTH_DB_FILE)
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return {"success": False, "message": "Username already exists"}
        
        # Check if email already exists
        if email:
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return {"success": False, "message": "Email already exists"}
        
        # Generate salt and hash password
        salt = generate_salt()
        password_hash = hash_password(password, salt)
        
        # Generate verification code
        verification_code = str(secrets.randbelow(1000000)).zfill(6)
        verification_expiry = datetime.now() + timedelta(hours=24)
        
        # Insert new user
        cursor.execute(
            '''INSERT INTO users 
            (username, email, password_hash, salt, mobile, verification_code, verification_code_expiry) 
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (username, email, password_hash, salt, mobile, verification_code, verification_expiry)
        )
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True, 
            "user_id": user_id, 
            "verification_code": verification_code,
            "message": "User registered successfully"
        }
    except Exception as e:
        print(f"Register user error: {e}")
        return {"success": False, "message": f"Registration failed: {str(e)}"}

def verify_user_credentials(username_or_email, password, ip_address=None):
    """Verify user credentials and log the attempt"""
    try:
        conn = sqlite3.connect(AUTH_DB_FILE)
        cursor = conn.cursor()
        
        # Check if it's an email (contains @) or username
        if '@' in username_or_email:
            cursor.execute(
                "SELECT id, username, password_hash, salt FROM users WHERE email = ?", 
                (username_or_email,)
            )
        else:
            cursor.execute(
                "SELECT id, username, password_hash, salt FROM users WHERE username = ?", 
                (username_or_email,)
            )
        
        user = cursor.fetchone()
        
        # Log the attempt
        if ip_address:
            cursor.execute(
                "INSERT INTO login_attempts (username, email, ip_address, success) VALUES (?, ?, ?, ?)",
                (
                    username_or_email if '@' not in username_or_email else None,
                    username_or_email if '@' in username_or_email else None,
                    ip_address,
                    False
                )
            )
            conn.commit()
        
        if not user:
            conn.close()
            return {"success": False, "message": "Invalid username/email or password"}
        
        user_id, username, password_hash, salt = user
        
        # Verify password
        if hash_password(password, salt) != password_hash:
            conn.close()
            return {"success": False, "message": "Invalid username/email or password"}
        
        # Update login attempt to success
        if ip_address:
            cursor.execute(
                "UPDATE login_attempts SET success = ? WHERE ip_address = ? AND username = ? ORDER BY attempt_time DESC LIMIT 1",
                (True, ip_address, username)
            )
        
        # Update last login time
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now(), user_id)
        )
        
        conn.commit()
        conn.close()
        
        return {"success": True, "user_id": user_id, "username": username}
    except Exception as e:
        print(f"Verify credentials error: {e}")
        return {"success": False, "message": f"Login failed: {str(e)}"}

def create_session(user_id, ip_address=None, user_agent=None):
    """Create a new session for a user"""
    try:
        conn = sqlite3.connect(AUTH_DB_FILE)
        cursor = conn.cursor()
        
        # Generate session token
        session_token = secrets.token_hex(32)
        
        # Set expiry to 30 days from now
        expires_at = datetime.now() + timedelta(days=30)
        
        cursor.execute(
            '''INSERT INTO sessions 
            (user_id, session_token, ip_address, user_agent, expires_at) 
            VALUES (?, ?, ?, ?, ?)''',
            (user_id, session_token, ip_address, user_agent, expires_at)
        )
        
        conn.commit()
        conn.close()
        
        return {"success": True, "session_token": session_token, "expires_at": expires_at}
    except Exception as e:
        print(f"Create session error: {e}")
        return {"success": False, "message": f"Failed to create session: {str(e)}"}

def validate_session(session_token):
    """Validate a session token"""
    try:
        conn = sqlite3.connect(AUTH_DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            '''SELECT s.id, s.user_id, s.expires_at, u.username, u.email 
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = ? AND s.expires_at > ?''',
            (session_token, datetime.now())
        )
        
        session = cursor.fetchone()
        conn.close()
        
        if not session:
            return {"success": False, "message": "Invalid or expired session"}
        
        session_id, user_id, expires_at, username, email = session
        
        return {
            "success": True, 
            "user_id": user_id,
            "username": username,
            "email": email,
            "expires_at": expires_at
        }
    except Exception as e:
        print(f"Validate session error: {e}")
        return {"success": False, "message": f"Session validation failed: {str(e)}"}

def end_session(session_token):
    """End a session by deleting it"""
    try:
        conn = sqlite3.connect(AUTH_DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM sessions WHERE session_token = ?", (session_token,))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Session ended successfully"}
    except Exception as e:
        print(f"End session error: {e}")
        return {"success": False, "message": f"Failed to end session: {str(e)}"}

def generate_verification_code(user_id):
    """Generate a new verification code for a user"""
    try:
        conn = sqlite3.connect(AUTH_DB_FILE)
        cursor = conn.cursor()
        
        # Generate verification code
        verification_code = str(secrets.randbelow(1000000)).zfill(6)
        verification_expiry = datetime.now() + timedelta(hours=24)
        
        cursor.execute(
            "UPDATE users SET verification_code = ?, verification_code_expiry = ? WHERE id = ?",
            (verification_code, verification_expiry, user_id)
        )
        
        conn.commit()
        conn.close()
        
        return {"success": True, "verification_code": verification_code}
    except Exception as e:
        print(f"Generate verification code error: {e}")
        return {"success": False, "message": f"Failed to generate verification code: {str(e)}"}

def verify_email(user_id, verification_code):
    """Verify a user's email with a verification code"""
    try:
        conn = sqlite3.connect(AUTH_DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT verification_code, verification_code_expiry FROM users WHERE id = ?",
            (user_id,)
        )
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {"success": False, "message": "User not found"}
        
        stored_code, expiry = result
        
        if stored_code != verification_code:
            conn.close()
            return {"success": False, "message": "Invalid verification code"}
        
        if datetime.fromisoformat(expiry) < datetime.now():
            conn.close()
            return {"success": False, "message": "Verification code expired"}
        
        cursor.execute(
            "UPDATE users SET is_email_verified = 1, verification_code = NULL WHERE id = ?",
            (user_id,)
        )
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Email verified successfully"}
    except Exception as e:
        print(f"Verify email error: {e}")
        return {"success": False, "message": f"Email verification failed: {str(e)}"}

def verify_mobile(user_id, verification_code):
    """Verify a user's mobile number with a verification code"""
    try:
        conn = sqlite3.connect(AUTH_DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT verification_code, verification_code_expiry FROM users WHERE id = ?",
            (user_id,)
        )
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {"success": False, "message": "User not found"}
        
        stored_code, expiry = result
        
        if stored_code != verification_code:
            conn.close()
            return {"success": False, "message": "Invalid verification code"}
        
        if datetime.fromisoformat(expiry) < datetime.now():
            conn.close()
            return {"success": False, "message": "Verification code expired"}
        
        cursor.execute(
            "UPDATE users SET is_mobile_verified = 1, verification_code = NULL WHERE id = ?",
            (user_id,)
        )
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Mobile verified successfully"}
    except Exception as e:
        print(f"Verify mobile error: {e}")
        return {"success": False, "message": f"Mobile verification failed: {str(e)}"}

def get_user_by_id(user_id):
    """Get user details by ID"""
    try:
        conn = sqlite3.connect(AUTH_DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT id, username, email, mobile, is_email_verified, 
            is_mobile_verified, last_login, created_at 
            FROM users WHERE id = ?""",
            (user_id,)
        )
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return {"success": False, "message": "User not found"}
        
        return {
            "success": True,
            "user": {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "mobile": user[3],
                "is_email_verified": bool(user[4]),
                "is_mobile_verified": bool(user[5]),
                "last_login": user[6],
                "created_at": user[7]
            }
        }
    except Exception as e:
        print(f"Get user error: {e}")
        return {"success": False, "message": f"Failed to get user: {str(e)}"}

def update_user(user_id, email=None, mobile=None, password=None):
    """Update user information"""
    try:
        conn = sqlite3.connect(AUTH_DB_FILE)
        cursor = conn.cursor()
        
        # Update email if provided
        if email:
            cursor.execute(
                "UPDATE users SET email = ?, is_email_verified = 0 WHERE id = ?",
                (email, user_id)
            )
        
        # Update mobile if provided
        if mobile:
            cursor.execute(
                "UPDATE users SET mobile = ?, is_mobile_verified = 0 WHERE id = ?",
                (mobile, user_id)
            )
        
        # Update password if provided
        if password:
            salt = generate_salt()
            password_hash = hash_password(password, salt)
            
            cursor.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
                (password_hash, salt, user_id)
            )
        
        # Update timestamp
        cursor.execute(
            "UPDATE users SET updated_at = ? WHERE id = ?",
            (datetime.now(), user_id)
        )
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "User updated successfully"}
    except Exception as e:
        print(f"Update user error: {e}")
        return {"success": False, "message": f"Failed to update user: {str(e)}"}

def get_login_history(user_id, limit=10):
    """Get login history for a user"""
    try:
        conn = sqlite3.connect(AUTH_DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT ip_address, user_agent, created_at
            FROM sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?""",
            (user_id, limit)
        )
        
        sessions = cursor.fetchall()
        conn.close()
        
        result = []
        for session in sessions:
            result.append({
                "ip_address": session[0],
                "user_agent": session[1],
                "login_time": session[2]
            })
        
        return {"success": True, "history": result}
    except Exception as e:
        print(f"Get login history error: {e}")
        return {"success": False, "message": f"Failed to get login history: {str(e)}"}