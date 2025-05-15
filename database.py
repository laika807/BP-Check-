import sqlite3
import pandas as pd
import os
from datetime import datetime

# Database setup
DB_FILE = "blood_pressure.db"

def setup_database():
    """Create database tables if they don't exist"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Create profiles table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            gender TEXT NOT NULL,
            age INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create blood pressure readings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            systolic INTEGER NOT NULL,
            diastolic INTEGER NOT NULL,
            heart_rate INTEGER,
            category TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database setup error: {e}")
        return False

# Ensure database is setup
setup_database()

def create_profile(name, gender, age):
    """Create a new profile and return the ID"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if maximum profiles (5) reached
        cursor.execute("SELECT COUNT(*) FROM profiles")
        count = cursor.fetchone()[0]
        
        if count >= 5:
            conn.close()
            return None
        
        # Insert new profile
        cursor.execute(
            "INSERT INTO profiles (name, gender, age) VALUES (?, ?, ?)",
            (name, gender, age)
        )
        
        profile_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return profile_id
    except Exception as e:
        print(f"Create profile error: {e}")
        return None

def get_profiles():
    """Get all profiles from the database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, gender, age FROM profiles ORDER BY name")
        profiles = cursor.fetchall()
        
        conn.close()
        
        # Convert to list of dictionaries
        result = []
        for profile in profiles:
            result.append({
                'id': profile[0],
                'name': profile[1],
                'gender': profile[2],
                'age': profile[3]
            })
        
        return result
    except Exception as e:
        print(f"Get profiles error: {e}")
        return []

def get_profile_by_id(profile_id):
    """Get a specific profile by ID"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, name, gender, age FROM profiles WHERE id = ?",
            (profile_id,)
        )
        profile = cursor.fetchone()
        
        conn.close()
        
        if profile:
            return {
                'id': profile[0],
                'name': profile[1],
                'gender': profile[2],
                'age': profile[3]
            }
        else:
            return None
    except Exception as e:
        print(f"Get profile by ID error: {e}")
        return None

def update_profile(profile_id, name, gender, age):
    """Update an existing profile"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE profiles SET name = ?, gender = ?, age = ? WHERE id = ?",
            (name, gender, age, profile_id)
        )
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Update profile error: {e}")
        return False

def delete_profile(profile_id):
    """Delete a profile and all associated readings"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Delete associated readings first
        cursor.execute("DELETE FROM readings WHERE profile_id = ?", (profile_id,))
        
        # Then delete the profile
        cursor.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Delete profile error: {e}")
        return False

def save_reading(profile_id, date, time, systolic, diastolic, heart_rate, category):
    """Save a new blood pressure reading"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Convert date to string format if it's a datetime object
        if isinstance(date, datetime):
            date = date.strftime('%Y-%m-%d')
        
        cursor.execute(
            """
            INSERT INTO readings 
            (profile_id, date, time, systolic, diastolic, heart_rate, category) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (profile_id, date, time, systolic, diastolic, heart_rate, category)
        )
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Save reading error: {e}")
        return False

def get_readings_by_profile(profile_id):
    """Get all readings for a specific profile"""
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # Join with profiles table to get profile information
        query = """
        SELECT r.id, r.date, r.time, r.systolic, r.diastolic, r.heart_rate, r.category,
               p.id as ProfileId, p.name as Name, p.gender as Gender, p.age as Age
        FROM readings r
        JOIN profiles p ON r.profile_id = p.id
        WHERE r.profile_id = ?
        ORDER BY r.date DESC, r.time DESC
        """
        
        df = pd.read_sql_query(query, conn, params=(profile_id,))
        
        conn.close()
        
        return df
    except Exception as e:
        print(f"Get readings by profile error: {e}")
        return pd.DataFrame()

def get_all_readings():
    """Get all blood pressure readings with profile information"""
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # Join with profiles table to get profile information
        query = """
        SELECT r.id, r.date, r.time, r.systolic, r.diastolic, r.heart_rate, r.category,
               p.id as ProfileId, p.name as Name, p.gender as Gender, p.age as Age
        FROM readings r
        JOIN profiles p ON r.profile_id = p.id
        ORDER BY r.date DESC, r.time DESC
        """
        
        df = pd.read_sql_query(query, conn)
        
        conn.close()
        
        return df
    except Exception as e:
        print(f"Get all readings error: {e}")
        return pd.DataFrame()

def delete_reading(reading_id):
    """Delete a specific reading"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM readings WHERE id = ?", (reading_id,))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Delete reading error: {e}")
        return False

def export_data_to_csv():
    """Export all data to CSV file"""
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # Get all readings with profile information
        query = """
        SELECT r.date, r.time, r.systolic, r.diastolic, r.heart_rate, r.category,
               p.name, p.gender, p.age
        FROM readings r
        JOIN profiles p ON r.profile_id = p.id
        ORDER BY p.name, r.date, r.time
        """
        
        df = pd.read_sql_query(query, conn)
        
        # Rename columns for better readability
        df.columns = ['Date', 'Time', 'Systolic', 'Diastolic', 'Heart Rate', 
                      'Category', 'Name', 'Gender', 'Age']
        
        conn.close()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"blood_pressure_export_{timestamp}.csv"
        
        # Save to CSV
        df.to_csv(filename, index=False)
        
        return filename
    except Exception as e:
        print(f"Export data error: {e}")
        return None
