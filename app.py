import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from utils import (categorize_bp, get_category_color, get_category_description,
                   calculate_statistics, get_educational_info)
import base64
import io
import database
import hashlib
import hmac
import os
import json
import auth_db
import auth_utils
import sms_utils

# Set page config
st.set_page_config(page_title="Blood Pressure Monitor",
                   page_icon="❤️",
                   layout="wide")
# Put the callback handler code right here :
query_params = st.experimental_get_query_params()
if "code" in query_params:
    result = auth_utils.process_google_callback(query_params["code"][0])
    if result["success"]:
        user_info = result["user_info"]
        ip = auth_utils.get_client_ip()
        ua = auth_utils.get_user_agent()
        login_result = auth_utils.login_or_register_with_google(user_info, ip, ua)
        if login_result["success"]:
            st.session_state.authenticated = True
            st.session_state.user_id = login_result["user_id"]
            st.session_state.username = login_result["username"]
            st.session_state.email = user_info.get("email")
            st.session_state.login_method = "google"
            st.session_state.auth_token = login_result["session_token"]
            st.success("Logged in with Google!")
            st.experimental_rerun()
        else:
            st.error(login_result["message"])
    else:
        st.error(result["message"])
      
# Initialize session state variables for authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "email" not in st.session_state:
    st.session_state.email = None
if "phone" not in st.session_state:
    st.session_state.phone = None
if "login_method" not in st.session_state:
    st.session_state.login_method = None
if "verification_needed" not in st.session_state:
    st.session_state.verification_needed = False
if "registration_step" not in st.session_state:
    st.session_state.registration_step = "initial"
if "temp_user_data" not in st.session_state:
    st.session_state.temp_user_data = {}
if "selected_profile_id" not in st.session_state:
    st.session_state.selected_profile_id = None
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "login"

# Function to reset session state for logout
def logout():
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.email = None
    st.session_state.phone = None
    st.session_state.login_method = None
    st.session_state.verification_needed = False
    st.session_state.registration_step = "initial"
    st.session_state.temp_user_data = {}
    st.session_state.current_tab = "login"
    # Don't reset selected_profile_id to maintain user preference

# Check if we have a session token in cookies
def check_session_token():
    if "auth_token" in st.session_state:
        token = st.session_state.auth_token
        # Validate session token
        result = auth_db.validate_session(token)
        if result["success"]:
            st.session_state.authenticated = True
            st.session_state.user_id = result["user_id"]
            st.session_state.username = result["username"]
            st.session_state.email = result.get("email")
            return True
    return False

# Function to set a session token
def set_session_token(token):
    st.session_state.auth_token = token

# Create a sidebar for authentication
with st.sidebar:
    if not st.session_state.authenticated:
        st.title("Login / Register")
        
        # Create tabs for login and registration
        login_tab, register_tab = st.tabs(["Login", "Register"])
        
        # Login form
        with login_tab:
            login_username = st.text_input("Username or Email", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            
            login_col1, login_col2 = st.columns(2)
            
            with login_col1:
                if st.button("Sign In"):
                    if login_username and login_password:
                        # Get client IP (simplified)
                        ip_address = auth_utils.get_client_ip()
                        
                        # Verify credentials
                        result = auth_db.verify_user_credentials(login_username, login_password, ip_address)
                        
                        if result["success"]:
                            # Create session
                            user_agent = auth_utils.get_user_agent()
                            session_result = auth_db.create_session(result["user_id"], ip_address, user_agent)
                            
                            if session_result["success"]:
                                # Set authenticated state
                                st.session_state.authenticated = True
                                st.session_state.user_id = result["user_id"]
                                st.session_state.username = result["username"]
                                st.session_state.login_method = "password"
                                
                                # Get user details
                                user_details = auth_db.get_user_by_id(result["user_id"])
                                if user_details["success"]:
                                    st.session_state.email = user_details["user"]["email"]
                                    st.session_state.phone = user_details["user"]["mobile"]
                                
                                # Store session token
                                set_session_token(session_result["session_token"])
                                
                                st.success("Login successful!")
                                st.rerun()
                            else:
                                st.error(session_result["message"])
                        else:
                            st.error(result["message"])
                    else:
                        st.error("Please enter both username/email and password")
            
            with login_col2:
                if st.button("Sign in with Google"):
    auth_url = 
  auth_utils.get_google_auth_url()
    st.markdown(f"[Click here to sign in with Google]({auth_url})",
                unsafe_allow_html=True)
        
        # Registration form
        with register_tab:
            if st.session_state.registration_step == "initial":
                reg_username = st.text_input("Choose a Username", key="reg_username")
                reg_email = st.text_input("Email Address", key="reg_email")
                reg_mobile = st.text_input("Mobile Number (optional)", key="reg_mobile")
                reg_password = st.text_input("Password", type="password", key="reg_password")
                reg_confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
                
                if st.button("Create Account"):
                    if not reg_username or not reg_email or not reg_password:
                        st.error("Username, email, and password are required")
                    elif reg_password != reg_confirm_password:
                        st.error("Passwords do not match")
                    else:
                        # Store in temp data
                        st.session_state.temp_user_data = {
                            "username": reg_username,
                            "email": reg_email,
                            "mobile": reg_mobile,
                            "password": reg_password
                        }
                        st.session_state.registration_step = "verification"
                        st.rerun()
            
            elif st.session_state.registration_step == "verification":
                st.subheader("Verify Your Information")
                st.write(f"Username: {st.session_state.temp_user_data['username']}")
                st.write(f"Email: {st.session_state.temp_user_data['email']}")
                if st.session_state.temp_user_data.get('mobile'):
                    st.write(f"Mobile: {st.session_state.temp_user_data['mobile']}")
                
                if st.button("Confirm and Create Account"):
                    # Register the user
                    result = auth_db.register_user(
                        st.session_state.temp_user_data["username"],
                        st.session_state.temp_user_data["email"],
                        st.session_state.temp_user_data["password"],
                        st.session_state.temp_user_data.get("mobile")
                    )
                    
                    if result["success"]:
                        st.success("Account created successfully! You can now log in.")
                        
                        # If email or mobile is provided, show verification info
                        if st.session_state.temp_user_data.get("email") or st.session_state.temp_user_data.get("mobile"):
                            st.info("A verification code has been generated. In a production app, this would be sent via email and/or SMS.")
                            # Only show code in development
                            st.code(result["verification_code"], language=None)
                        
                        st.session_state.registration_step = "complete"
                        # Reset temp data
                        st.session_state.temp_user_data = {}
                    else:
                        st.error(result["message"])
                
                if st.button("Go Back"):
                    st.session_state.registration_step = "initial"
                    st.rerun()
            
            elif st.session_state.registration_step == "complete":
                st.success("Registration complete! Please login with your credentials.")
                if st.button("Go to Login"):
                    st.session_state.registration_step = "initial"
                    st.rerun()
        
        # Google login information (for demonstration)
        if st.session_state.current_tab == "google_info":
            st.info("Google Authentication Simulation")
            st.write("In a real app, this would be handled by Google OAuth.")
            st.write("For demonstration, we'll simulate a successful Google login.")
            
            if st.button("Simulate Successful Google Login"):
                # Create a user if not exists
                username = st.session_state.temp_user_data["username"]
                email = st.session_state.temp_user_data["email"]
                
                # Check if user exists
                exists = auth_utils.check_user_exists_by_email(email)
                
                if not exists:
                    # Register new user with random password
                    password = auth_utils.generate_secure_random_password()
                    result = auth_db.register_user(username, email, password)
                    if not result["success"]:
                        st.error(result["message"])
                        st.stop()
                
                # Login with email
                ip_address = auth_utils.get_client_ip()
                user_agent = auth_utils.get_user_agent()
                result = auth_utils.login_with_email(email, ip_address, user_agent)
                
                if result["success"]:
                    # Set authenticated state
                    st.session_state.authenticated = True
                    st.session_state.user_id = result["user_id"]
                    st.session_state.username = result["username"]
                    st.session_state.email = email
                    st.session_state.login_method = "google"
                    
                    # Store session token
                    set_session_token(result["session_token"])
                    
                    st.success("Google login successful!")
                    st.rerun()
                else:
                    st.error(result["message"])
    
    else:
        # User is authenticated - show profile sidebar
        st.title(f"Hello, {st.session_state.username}!")
        
        if st.session_state.email:
            st.write(f"Email: {st.session_state.email}")
        
        if st.session_state.phone:
            st.write(f"Phone: {st.session_state.phone}")
        
        # Account management
        st.subheader("Account Settings")
        
        # Navigation for authenticated users
        if st.button("My Dashboard"):
            st.session_state.current_tab = "dashboard"
        
        if st.button("My Profile Settings"):
            st.session_state.current_tab = "profile_settings"
        
        # Logout option
        if st.button("Logout"):
            # End session in database
            if "auth_token" in st.session_state:
                auth_db.end_session(st.session_state.auth_token)
            
            # Clear session state
            logout()
            st.rerun()

# If not authenticated, show only the welcome screen
if not st.session_state.authenticated:
    st.title("Blood Pressure Monitor")
    st.markdown("""
        Welcome to the Blood Pressure Monitor application!
        
        This secure platform allows you to:
        
        * Track blood pressure readings over time
        * Create profiles for family members
        * Visualize blood pressure trends
        * Get alerts for concerning readings
        * Access educational information about blood pressure
        
        To get started, please login or create an account using the sidebar.
    """)
    
    # Show features and screenshots
    st.subheader("Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🔒 Secure")
        st.markdown("Your health data is protected with secure authentication")
    
    with col2:
        st.markdown("### 📊 Analytics")
        st.markdown("Visualize your blood pressure trends over time")
    
    with col3:
        st.markdown("### 👪 Multi-Profile")
        st.markdown("Track readings for up to 5 family members")
    
    st.stop()  # Stop execution if not authenticated

# If we reach here, the user is authenticated - continue with the main app functionality

# Load data from database
try:
    # Get all readings from the database
    db_data = database.get_all_readings()

    # Initialize session state with data from database
    if 'bp_data' not in st.session_state:
        st.session_state.bp_data = db_data if not db_data.empty else pd.DataFrame(
            {
                'Date': pd.Series(dtype='object'),
                'Time': pd.Series(dtype='object'),
                'Systolic': pd.Series(dtype='int'),
                'Diastolic': pd.Series(dtype='int'),
                'HeartRate': pd.Series(dtype='int'),
                'Gender': pd.Series(dtype='object'),
                'Age': pd.Series(dtype='int'),
                'Category': pd.Series(dtype='object')
            })
except Exception as e:
    st.error(f"Error loading data from database: {e}")
    # Fallback to empty DataFrame if database fails
    if 'bp_data' not in st.session_state:
        st.session_state.bp_data = pd.DataFrame({
            'Date':
            pd.Series(dtype='object'),
            'Time':
            pd.Series(dtype='object'),
            'Systolic':
            pd.Series(dtype='int'),
            'Diastolic':
            pd.Series(dtype='int'),
            'HeartRate':
            pd.Series(dtype='int'),
            'Gender':
            pd.Series(dtype='object'),
            'Age':
            pd.Series(dtype='int'),
            'Category':
            pd.Series(dtype='object')
        })

# App title and description
st.title("Blood Pressure Monitor")
st.markdown("""
    Track, analyze, and monitor your blood pressure readings over time.
    Create profiles for up to 5 people and easily track their measurements.
""")

# Add tabs for main interface, profile management, and analytics
tab1, tab2, tab3 = st.tabs(
    ["Blood Pressure Readings", "Manage Profiles", "My Profile Analytics"])
try:
    # Get all readings from the database
    db_data = database.get_all_readings()

    # Initialize session state with data from database
    if 'bp_data' not in st.session_state:
        st.session_state.bp_data = db_data if not db_data.empty else pd.DataFrame(
            {
                'Date': pd.Series(dtype='object'),
                'Time': pd.Series(dtype='object'),
                'Systolic': pd.Series(dtype='int'),
                'Diastolic': pd.Series(dtype='int'),
                'HeartRate': pd.Series(dtype='int'),
                'Gender': pd.Series(dtype='object'),
                'Age': pd.Series(dtype='int'),
                'Category': pd.Series(dtype='object')
            })
except Exception as e:
    st.error(f"Error loading data from database: {e}")
    # Fallback to empty DataFrame if database fails
    if 'bp_data' not in st.session_state:
        st.session_state.bp_data = pd.DataFrame({
            'Date':
            pd.Series(dtype='object'),
            'Time':
            pd.Series(dtype='object'),
            'Systolic':
            pd.Series(dtype='int'),
            'Diastolic':
            pd.Series(dtype='int'),
            'HeartRate':
            pd.Series(dtype='int'),
            'Gender':
            pd.Series(dtype='object'),
            'Age':
            pd.Series(dtype='int'),
            'Category':
            pd.Series(dtype='object')
        })

# App title and description
st.title("Blood Pressure Monitor")
st.markdown("""
    Track, analyze, and monitor your blood pressure readings over time.
    Create profiles for up to 5 people and easily track their measurements.
""")

# Add tabs for main interface, profile management, and analytics
tab1, tab2, tab3 = st.tabs(
    ["Blood Pressure Readings", "Manage Profiles", "My Profile Analytics"])

with tab2:
    st.subheader("Profile Management")
    st.markdown("Create and manage profiles for up to 5 people.")

    # Get all profiles
    profiles = database.get_profiles()

    # Display existing profiles
    if profiles:
        st.write(f"Current Profiles ({len(profiles)}/5):")
        for i, profile in enumerate(profiles):
            with st.expander(
                    f"{profile['name']} ({profile['gender']}, {profile['age']} years)"
            ):
                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    new_name = st.text_input(f"Name",
                                             value=profile['name'],
                                             key=f"name_{profile['id']}")

                with col2:
                    new_gender = st.selectbox(
                        f"Gender",
                        options=["Male", "Female"],
                        index=0 if profile['gender'] == "Male" else 1,
                        key=f"gender_{profile['id']}")

                with col3:
                    new_age = st.number_input(f"Age",
                                              min_value=1,
                                              max_value=120,
                                              value=profile['age'],
                                              key=f"age_{profile['id']}")

                update_col, delete_col = st.columns(2)

                with update_col:
                    if st.button("Update Profile",
                                 key=f"update_{profile['id']}"):
                        if database.update_profile(profile['id'], new_name,
                                                   new_gender, new_age):
                            st.success("Profile updated successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to update profile.")

                with delete_col:
                    if st.button("Delete Profile",
                                 key=f"delete_{profile['id']}"):
                        if database.delete_profile(profile['id']):
                            st.success("Profile deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to delete profile.")
    else:
        st.info("No profiles created yet. Add your first profile below.")

    # Add new profile form
    if len(profiles) < 5:
        st.markdown("---")
        st.subheader("Add New Profile")

        with st.form("add_profile_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_profile_name = st.text_input("Name")
                new_profile_gender = st.selectbox("Gender",
                                                  options=["Male", "Female"])

            with col2:
                new_profile_age = st.number_input("Age",
                                                  min_value=1,
                                                  max_value=120,
                                                  value=40)

            submitted = st.form_submit_button("Create Profile")

            if submitted:
                if new_profile_name:
                    profile_id = database.create_profile(
                        new_profile_name, new_profile_gender, new_profile_age)
                    if profile_id:
                        st.success(f"Profile created successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to create profile.")
                else:
                    st.error("Profile name is required.")

with tab1:
    # Main app layout with columns
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Enter Blood Pressure Reading")

        # Get profiles for selection
        profiles = database.get_profiles()

        if not profiles:
            st.warning("Please create a profile first before adding readings.")
            st.info("Go to the 'Manage Profiles' tab to create a profile.")
        else:
            # Profile selection
            profile_options = {
                f"{p['name']} ({p['gender']}, {p['age']} years)": p['id']
                for p in profiles
            }
            profile_display_name = st.selectbox("Select Profile",
                                                options=list(
                                                    profile_options.keys()))
            selected_profile_id = profile_options[profile_display_name]

            # Get selected profile details
            selected_profile = database.get_profile_by_id(selected_profile_id)

            # Date and time input - with current date and time as default
            current_date = datetime.now().date()
            current_time = datetime.now().time().replace(microsecond=0)

            date = st.date_input("Date", value=current_date)
            time = st.time_input("Time", value=current_time)

            # Blood pressure inputs with validation
            systolic = st.number_input("Upper wala (Systolic) (mmHg)",
                                       min_value=70,
                                       max_value=250,
                                       value=120,
                                       step=1)
            diastolic = st.number_input("Niche wala (Diastolic) (mmHg)",
                                        min_value=40,
                                        max_value=150,
                                        value=80,
                                        step=1)

            # Heart rate (optional)
            heart_rate = st.number_input("Heart Rate (BPM, optional)",
                                         min_value=30,
                                         max_value=220,
                                         value=75,
                                         step=1)

            # Display profile information (read-only)
            st.info(
                f"Reading will be saved for: {selected_profile['name']} ({selected_profile['gender']}, {selected_profile['age']} years)"
            )

            # Submit button
            submit = st.button("Save Reading")

            if submit:
                # Categorize the blood pressure with gender and age considerations
                gender = selected_profile['gender']
                age = selected_profile['age']
                category = categorize_bp(systolic, diastolic, gender, age)

                # Format time as string
                time_str = time.strftime('%H:%M')

                # Save to database
                success = database.save_reading(profile_id=selected_profile_id,
                                                date=date,
                                                time=time_str,
                                                systolic=systolic,
                                                diastolic=diastolic,
                                                heart_rate=heart_rate,
                                                category=category)

                if success:
                    # Create a new entry for session state
                    new_entry = pd.DataFrame([{
                        'Date': date,
                        'Time': time_str,
                        'ProfileId': selected_profile_id,
                        'Name': selected_profile['name'],
                        'Gender': gender,
                        'Age': age,
                        'Systolic': systolic,
                        'Diastolic': diastolic,
                        'HeartRate': heart_rate,
                        'Category': category
                    }])

                    # Add to session state
                    st.session_state.bp_data = pd.concat(
                        [st.session_state.bp_data, new_entry],
                        ignore_index=True)

                    st.success("Reading saved successfully!")
                    st.rerun()
                else:
                    st.error(
                        "Failed to save reading to database. Please try again."
                    )

    with col2:
        # Only show this if we have data
        if not st.session_state.bp_data.empty:
            # Get the latest reading
            latest = st.session_state.bp_data.iloc[-1]
            category = latest['Category']

            st.subheader("Latest Reading")

            # Display latest reading with large numbers and color coding
            col_a, col_b, col_c = st.columns([1, 1, 1])

            with col_a:
                st.metric(label="Upper wala (Systolic)",
                        value=f"{latest['Systolic']} mmHg")
            with col_b:
                st.metric(label="Niche wala (Diastolic)",
                        value=f"{latest['Diastolic']} mmHg")
            with col_c:
                if 'HeartRate' in latest and latest['HeartRate'] > 0:
                    st.metric(label="Heart Rate",
                            value=f"{latest['HeartRate']} BPM")

            # Show profile information if available
            if 'Name' in latest:
                st.markdown(
                    f"**Person**: {latest['Name']} ({latest['Gender']}, {latest['Age']} years)"
                )

            # Show category with appropriate color - simplified display
            color = get_category_color(category)
            st.markdown(
                f"<div style='background-color:{color}; padding:10px; border-radius:5px;'>"
                f"<h2 style='color:white; text-align:center;'>{category}</h2></div>",
                unsafe_allow_html=True)
            
            # Show category description
            st.markdown(get_category_description(category))
        else:
            st.info(
                "No readings yet. Enter your first blood pressure reading to get started."
            )

# Create tab3 content for Analytics
with tab3:
    st.subheader("My Profile Analytics")

    if st.session_state.bp_data.empty:
        st.info(
            "No blood pressure readings found. Please add readings in the 'Blood Pressure Readings' tab."
        )
    else:
        # Add profile filter if we have profile data
        selected_profile_for_viz = None
        filtered_data = st.session_state.bp_data
        
        if 'ProfileId' in st.session_state.bp_data.columns:
            profiles = database.get_profiles()
            if profiles:
                profile_options = {"All Profiles": None}
                profile_options.update({
                    f"{p['name']} ({p['gender']}, {p['age']} years)":
                    p['id'] for p in profiles
                })
                
                selected_profile_name = st.selectbox(
                    "Select Profile for Analysis",
                    options=list(profile_options.keys()),
                    key="profile_viz"
                )
                
                selected_profile_for_viz = profile_options[selected_profile_name]
                
                # Filter data if a specific profile is selected
                if selected_profile_for_viz:
                    filtered_data = st.session_state.bp_data[
                        st.session_state.bp_data['ProfileId'] == selected_profile_for_viz
                    ]
        
        # Time range filter
        st.subheader("Time Range")
        time_range = st.selectbox(
            "Select Time Range",
            options=["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days"],
            key="time_range"
        )
        
        # Apply time filter
        if time_range != "All Time" and 'Date' in filtered_data.columns:
            if isinstance(filtered_data['Date'].iloc[0], str):
                filtered_data['Date'] = pd.to_datetime(filtered_data['Date'])
            
            today = datetime.now().date()
            if time_range == "Last 7 Days":
                start_date = today - timedelta(days=7)
            elif time_range == "Last 30 Days":
                start_date = today - timedelta(days=30)
            elif time_range == "Last 90 Days":
                start_date = today - timedelta(days=90)
                
            filtered_data = filtered_data[filtered_data['Date'] >= start_date]
        
        # If no data after filtering
        if filtered_data.empty:
            st.warning("No data available for the selected profile and time range.")
        else:
            # Calculate statistics
            stats = calculate_statistics(filtered_data)
            
            # Display statistics in expandable section
            with st.expander("Statistics Summary", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Average Systolic", f"{stats['avg_systolic']:.1f} mmHg")
                    st.metric("Min Systolic", f"{stats['min_systolic']} mmHg")
                    st.metric("Max Systolic", f"{stats['max_systolic']} mmHg")
                
                with col2:
                    st.metric("Average Diastolic", f"{stats['avg_diastolic']:.1f} mmHg")
                    st.metric("Min Diastolic", f"{stats['min_diastolic']} mmHg")
                    st.metric("Max Diastolic", f"{stats['max_diastolic']} mmHg")
                
                with col3:
                    if 'HeartRate' in filtered_data.columns:
                        st.metric("Average Heart Rate", f"{stats['avg_heart_rate']:.1f} BPM")
                        st.metric("Min Heart Rate", f"{stats['min_heart_rate']} BPM")
                        st.metric("Max Heart Rate", f"{stats['max_heart_rate']} BPM")
            
            # Time series visualization
            st.subheader("Blood Pressure Trends")
            
            # Convert date column to datetime if it's not already
            if not pd.api.types.is_datetime64_any_dtype(filtered_data['Date']):
                filtered_data['Date'] = pd.to_datetime(filtered_data['Date'])
            
            # Sort by date for proper timeline
            plot_data = filtered_data.sort_values('Date')
            
            # Create a time series plot
            fig = go.Figure()
            
            # Add traces for systolic and diastolic
            fig.add_trace(go.Scatter(
                x=plot_data['Date'],
                y=plot_data['Systolic'],
                mode='lines+markers',
                name='Systolic',
                line=dict(color='red', width=2),
                marker=dict(size=8)
            ))
            
            fig.add_trace(go.Scatter(
                x=plot_data['Date'],
                y=plot_data['Diastolic'],
                mode='lines+markers',
                name='Diastolic',
                line=dict(color='blue', width=2),
                marker=dict(size=8)
            ))
            
            # Add heart rate if available
            if 'HeartRate' in plot_data.columns and plot_data['HeartRate'].notna().any():
                fig.add_trace(go.Scatter(
                    x=plot_data['Date'],
                    y=plot_data['HeartRate'],
                    mode='lines+markers',
                    name='Heart Rate',
                    line=dict(color='green', width=2),
                    marker=dict(size=8),
                    yaxis="y2"
                ))
                
                # Add secondary y-axis for heart rate
                fig.update_layout(
                    yaxis2=dict(
                        title="Heart Rate (BPM)",
                        overlaying="y",
                        side="right",
                        range=[30, 180]
                    )
                )
            
            # Update layout
            fig.update_layout(
                title="Blood Pressure Over Time",
                xaxis_title="Date",
                yaxis_title="Blood Pressure (mmHg)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=500,
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            # Add reference lines for normal ranges
            fig.add_shape(
                type="line",
                x0=plot_data['Date'].min(),
                x1=plot_data['Date'].max(),
                y0=120,
                y1=120,
                line=dict(color="rgba(255,0,0,0.3)", width=2, dash="dash"),
                name="Systolic Reference"
            )
            
            fig.add_shape(
                type="line",
                x0=plot_data['Date'].min(),
                x1=plot_data['Date'].max(),
                y0=80,
                y1=80,
                line=dict(color="rgba(0,0,255,0.3)", width=2, dash="dash"),
                name="Diastolic Reference"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Distribution of readings by category
            st.subheader("Blood Pressure Categories")
            
            # Create a bar chart showing count by category
            category_counts = plot_data['Category'].value_counts().reset_index()
            category_counts.columns = ['Category', 'Count']
            
            fig_categories = px.bar(
                category_counts,
                x='Category',
                y='Count',
                color='Category',
                color_discrete_map={
                    'Normal': 'green',
                    'Elevated': 'yellow',
                    'Hypertension Stage 1': 'orange',
                    'Hypertension Stage 2': 'red',
                    'Hypertensive Crisis': 'darkred'
                }
            )
            
            fig_categories.update_layout(
                title="Distribution of Blood Pressure Readings by Category",
                xaxis_title="Category",
                yaxis_title="Number of Readings",
                height=400
            )
            
            st.plotly_chart(fig_categories, use_container_width=True)
            
            # Data table with all readings
            st.subheader("All Readings")
            
            # Show a downloadable CSV option
            def convert_df_to_csv(df):
                csv = df.to_csv(index=False)
                return csv
            
            display_data = filtered_data.sort_values(by=['Date', 'Time'], ascending=[False, False])
            if 'ProfileId' in display_data.columns:
                display_data = display_data.drop(columns=['ProfileId'])
            
            csv = convert_df_to_csv(display_data)
            st.download_button(
                label="Download Data as CSV",
                data=csv,
                file_name='blood_pressure_data.csv',
                mime='text/csv',
            )
            
            # Show the data table
            st.dataframe(display_data, use_container_width=True)
    
    # Educational section
    st.subheader("Blood Pressure Education")
    educational_info = get_educational_info()
    
    with st.expander("Understanding Blood Pressure"):
        st.markdown(educational_info['understanding'])
        
    with st.expander("Blood Pressure Categories"):
        st.markdown(educational_info['categories'])
        
    with st.expander("Tips for Managing Blood Pressure"):
        st.markdown(educational_info['tips'])
