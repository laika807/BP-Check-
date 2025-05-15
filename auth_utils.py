import os
import json
import base64
import hashlib
import requests
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import urlencode
import streamlit as st
import auth_db

# Always import time for our JWT implementation
import time

# Try to import JWT - if not available, use a fallback
try:
    import jwt
    HAS_JWT = True
except ImportError:
    print("PyJWT package not found. Using fallback token generation.")
    HAS_JWT = False
    
    # Define error classes to match JWT's
    class ExpiredSignatureError(Exception): pass
    class InvalidTokenError(Exception): pass
    
    # Basic fallback for JWT functionality
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

# Google OAuth Configuration
# These would typically come from environment variables
GOOGLE_CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = st.secrets.get("REDIRECT_URI", "http://localhost:5000")

# JWT Configuration
JWT_SECRET = st.secrets.get("JWT_SECRET", "your-secret-key-here")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

def get_google_auth_url():
    """Generate Google OAuth authorization URL"""
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': 'openid email profile',
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent',
    }
    return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"

def exchange_code_for_token(code):
    """Exchange authorization code for access token"""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        return None
    
    return response.json()

def get_google_user_info(token_data):
    """Get user info from Google using access token"""
    user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    headers = {'Authorization': f"Bearer {token_data['access_token']}"}
    
    response = requests.get(user_info_url, headers=headers)
    if response.status_code != 200:
        return None
    
    return response.json()

def process_google_callback(code):
    """Process Google OAuth callback and get user info"""
    token_data = exchange_code_for_token(code)
    if not token_data:
        return {"success": False, "message": "Failed to exchange code for token"}
    
    user_info = get_google_user_info(token_data)
    if not user_info:
        return {"success": False, "message": "Failed to get user info"}
    
    return {
        "success": True,
        "user_info": {
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
            "given_name": user_info.get("given_name"),
            "family_name": user_info.get("family_name"),
            "locale": user_info.get("locale"),
            "verified_email": user_info.get("verified_email", False)
        }
    }

def login_or_register_with_google(user_info, ip_address=None, user_agent=None):
    """Login or register a user with Google info"""
    email = user_info.get("email")
    if not email:
        return {"success": False, "message": "No email provided by Google"}
    
    # Check if user exists
    exists = check_user_exists_by_email(email)
    
    if exists:
        # User exists, log them in
        return login_with_email(email, ip_address, user_agent)
    else:
        # Register new user
        username = generate_username_from_email(email)
        password = generate_secure_random_password()
        
        register_result = auth_db.register_user(username, email, password)
        
        if not register_result["success"]:
            return register_result
        
        # If registration succeeded, automatically verify email since Google verified it
        if user_info.get("verified_email", False):
            user_id = register_result["user_id"]
            auth_db.verify_email(user_id, register_result["verification_code"])
        
        # Log in the newly registered user
        return login_with_email(email, ip_address, user_agent)

def check_user_exists_by_email(email):
    """Check if a user exists by email"""
    conn = sqlite3.connect(auth_db.AUTH_DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    result = cursor.fetchone()
    
    conn.close()
    
    return result is not None

def generate_username_from_email(email):
    """Generate a username from email address"""
    # Take part before @ and add a random suffix
    import random
    username_base = email.split('@')[0]
    random_suffix = str(random.randint(1000, 9999))
    
    username = f"{username_base}_{random_suffix}"
    return username

def generate_secure_random_password():
    """Generate a secure random password"""
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(alphabet) for i in range(16))
    
    return password

def login_with_email(email, ip_address=None, user_agent=None):
    """Login user with email"""
    conn = sqlite3.connect(auth_db.AUTH_DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username FROM users WHERE email = ?", (email,))
    result = cursor.fetchone()
    
    conn.close()
    
    if not result:
        return {"success": False, "message": "User not found"}
    
    user_id, username = result
    
    # Create session
    session_result = auth_db.create_session(user_id, ip_address, user_agent)
    
    if not session_result["success"]:
        return session_result
    
    return {
        "success": True,
        "user_id": user_id,
        "username": username,
        "session_token": session_result["session_token"]
    }

def get_client_ip():
    """Get client IP address from Streamlit session"""
    try:
        # This is a placeholder as Streamlit doesn't directly expose client IP
        # In a real app, you might use a server-side approach or an API
        return "127.0.0.1"
    except:
        return None

def get_user_agent():
    """Get user agent from Streamlit session"""
    try:
        # This is a placeholder as Streamlit doesn't directly expose user agent
        return "Streamlit Client"
    except:
        return None

def generate_jwt_token(user_id, username):
    """Generate a JWT token for the user"""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def validate_jwt_token(token):
    """Validate a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {
            "success": True,
            "user_id": payload["user_id"],
            "username": payload["username"]
        }
    except jwt.ExpiredSignatureError:
        return {"success": False, "message": "Token expired"}
    except jwt.InvalidTokenError:
        return {"success": False, "message": "Invalid token"}

def send_email_verification(email, code):
    """
    Send verification email (placeholder)
    
    In a real app, you would integrate with a service like SendGrid, 
    Mailgun, SES, etc. to send actual emails.
    """
    # For development, just print the code
    print(f"[EMAIL] Verification code for {email}: {code}")
    return True

def send_sms_verification(phone_number, code):
    """
    Send verification SMS (placeholder)
    
    In a real app, you would integrate with a service like Twilio, 
    Nexmo, etc. to send actual SMS messages.
    """
    # For development, just print the code
    print(f"[SMS] Verification code for {phone_number}: {code}")
    return True