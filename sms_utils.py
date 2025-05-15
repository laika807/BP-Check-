import os
import streamlit as st

def send_sms_notification(to_phone_number, message):
    """
    Send SMS notification using Twilio
    
    Args:
        to_phone_number (str): The recipient's phone number in E.164 format
        message (str): The message content to send
        
    Returns:
        dict: Response with success status and details
    """
    # Check if Twilio credentials are available
    try:
        from twilio.rest import Client
        
        # Get Twilio credentials from secrets
        account_sid = st.secrets.get("TWILIO_ACCOUNT_SID", "")
        auth_token = st.secrets.get("TWILIO_AUTH_TOKEN", "")
        from_phone = st.secrets.get("TWILIO_PHONE_NUMBER", "")
        
        if not account_sid or not auth_token or not from_phone:
            return {
                "success": False,
                "message": "Twilio credentials are not configured. Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in your secrets."
            }
            
        # Initialize Twilio client
        client = Client(account_sid, auth_token)
        
        # Send SMS
        sms = client.messages.create(
            body=message,
            from_=from_phone,
            to=to_phone_number
        )
        
        return {
            "success": True,
            "message": "SMS sent successfully",
            "sid": sms.sid
        }
        
    except ImportError:
        return {
            "success": False,
            "message": "Twilio package is not installed. Please install it using 'pip install twilio'."
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to send SMS: {str(e)}"
        }

def send_verification_code(phone_number, code):
    """
    Send verification code via SMS
    
    Args:
        phone_number (str): The recipient's phone number
        code (str): The verification code
        
    Returns:
        dict: Response with success status and details
    """
    message = f"Your Blood Pressure Monitor verification code is: {code}. This code will expire in 24 hours."
    return send_sms_notification(phone_number, message)

def send_bp_alert(phone_number, user_name, systolic, diastolic, category):
    """
    Send blood pressure alert via SMS
    
    Args:
        phone_number (str): The recipient's phone number
        user_name (str): The user's name
        systolic (int): Systolic blood pressure reading
        diastolic (int): Diastolic blood pressure reading
        category (str): Blood pressure category
        
    Returns:
        dict: Response with success status and details
    """
    message = f"ALERT: {user_name}'s blood pressure reading of {systolic}/{diastolic} mmHg is categorized as '{category}'. Please take appropriate action."
    return send_sms_notification(phone_number, message)

def format_phone_number(phone_number):
    """
    Format a phone number to E.164 format
    
    Args:
        phone_number (str): The input phone number
        
    Returns:
        str: Formatted phone number or None if invalid
    """
    # Remove any non-digit characters
    digits = ''.join(filter(str.isdigit, phone_number))
    
    # Add country code if missing
    if len(digits) == 10:  # Assuming US phone number without country code
        return f"+1{digits}"
    elif len(digits) > 10 and not digits.startswith('+'):
        return f"+{digits}"
    
    return digits