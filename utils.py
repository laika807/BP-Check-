import pandas as pd
import numpy as np

def categorize_bp(systolic, diastolic, gender, age):
    """
    Categorize blood pressure reading according to medical standards.
    Takes into account gender and age differences.
    
    Returns: Category string
    """
    # Age factor adjustment - older people tend to have higher BP
    age_factor_systolic = 0
    age_factor_diastolic = 0
    
    if age > 60:
        age_factor_systolic = 5
        age_factor_diastolic = 3
    elif age > 50:
        age_factor_systolic = 3
        age_factor_diastolic = 2
    
    # Gender adjustments - women tend to have slightly lower BP than men
    gender_factor_systolic = -3 if gender == "Female" else 0
    gender_factor_diastolic = -2 if gender == "Female" else 0
    
    # Adjust the readings based on age and gender
    adjusted_systolic = systolic - age_factor_systolic - gender_factor_systolic
    adjusted_diastolic = diastolic - age_factor_diastolic - gender_factor_diastolic
    
    # Categorize according to standard guidelines
    if adjusted_systolic >= 180 or adjusted_diastolic >= 120:
        return "Hypertensive Crisis"
    elif adjusted_systolic >= 140 or adjusted_diastolic >= 90:
        return "Hypertension Stage 2"
    elif (adjusted_systolic >= 130 and adjusted_systolic < 140) or (adjusted_diastolic >= 80 and adjusted_diastolic < 90):
        return "Hypertension Stage 1"
    elif adjusted_systolic >= 120 and adjusted_systolic < 130 and adjusted_diastolic < 80:
        return "Elevated"
    else:
        return "Normal"

def get_category_color(category):
    """Return a color based on blood pressure category."""
    colors = {
        "Normal": "#4CAF50",  # Green
        "Elevated": "#FFEB3B",  # Yellow
        "Hypertension Stage 1": "#FF9800",  # Orange
        "Hypertension Stage 2": "#F44336",  # Red
        "Hypertensive Crisis": "#B71C1C",  # Dark Red
    }
    return colors.get(category, "#757575")  # Default gray

def get_category_description(category):
    """Return a description for each blood pressure category."""
    descriptions = {
        "Normal": """
        **Normal Blood Pressure:**
        Your blood pressure is within the normal range. Continue with healthy habits like:
        - Regular exercise
        - Balanced diet low in sodium
        - Maintaining healthy weight
        - Limited alcohol consumption
        """,
        "Elevated": """
        **Elevated Blood Pressure:**
        Your blood pressure is slightly above normal. Consider lifestyle changes to prevent progression to hypertension:
        - Reduce sodium intake
        - Regular physical activity
        - Limit alcohol
        - Manage stress
        """,
        "Hypertension Stage 1": """
        **Hypertension Stage 1:**
        Your blood pressure is elevated. Consider speaking with your doctor about:
        - Lifestyle modifications
        - Potential medication
        - Regular monitoring
        - Heart-healthy diet
        """,
        "Hypertension Stage 2": """
        **Hypertension Stage 2:**
        Your blood pressure is significantly elevated. Consult with your doctor promptly about:
        - Medication options
        - Strict dietary changes
        - Regular exercise regimen
        - Frequent BP monitoring
        """,
        "Hypertensive Crisis": """
        **Hypertensive Crisis - Seek Immediate Medical Attention!**
        This is a medical emergency. Contact your doctor immediately or go to the emergency room if you're also experiencing:
        - Chest pain
        - Shortness of breath
        - Back pain
        - Numbness/weakness
        - Change in vision
        - Difficulty speaking
        """
    }
    return descriptions.get(category, "No description available.")

def calculate_statistics(df):
    """Calculate statistics from blood pressure data."""
    stats = {
        'avg_systolic': df['Systolic'].mean(),
        'min_systolic': df['Systolic'].min(),
        'max_systolic': df['Systolic'].max(),
        'avg_diastolic': df['Diastolic'].mean(),
        'min_diastolic': df['Diastolic'].min(),
        'max_diastolic': df['Diastolic'].max(),
    }
    
    # Add heart rate stats if available
    if 'HeartRate' in df.columns and not df['HeartRate'].empty:
        stats.update({
            'avg_heart_rate': df['HeartRate'].mean(),
            'min_heart_rate': df['HeartRate'].min(),
            'max_heart_rate': df['HeartRate'].max(),
        })
    else:
        stats.update({
            'avg_heart_rate': 0,
            'min_heart_rate': 0,
            'max_heart_rate': 0,
        })
    
    return stats

def get_educational_info():
    """Return educational information about blood pressure."""
    return {
        'understanding': """
        ### Understanding Blood Pressure
        
        Blood pressure is the force of blood pushing against the walls of your arteries as your heart pumps blood. It's measured using two numbers:
        
        - **Systolic pressure (upper number)**: The pressure when your heart beats and pushes blood through the arteries
        - **Diastolic pressure (lower number)**: The pressure when your heart rests between beats
        
        Blood pressure is written as systolic pressure over diastolic pressure, like 120/80 mmHg ("millimeters of mercury").
        
        High blood pressure (hypertension) puts extra strain on your heart and blood vessels, which can lead to heart attacks, strokes, and other serious health problems if left untreated.
        """,
        
        'categories': """
        ### Blood Pressure Categories
        
        | Category | Systolic (mmHg) | Diastolic (mmHg) |
        |----------|-----------------|------------------|
        | Normal | Less than 120 | Less than 80 |
        | Elevated | 120-129 | Less than 80 |
        | Hypertension Stage 1 | 130-139 | 80-89 |
        | Hypertension Stage 2 | 140 or higher | 90 or higher |
        | Hypertensive Crisis | Higher than 180 | Higher than 120 |
        
        *Note: These categories apply to most adults. Children, pregnant women, and certain medical conditions may have different guidelines.*
        """,
        
        'tips': """
        ### Tips for Managing Blood Pressure
        
        1. **Maintain a healthy diet**
           - Reduce sodium (salt) intake
           - Eat plenty of fruits, vegetables, and whole grains
           - Limit saturated and trans fats
           - Consider the DASH (Dietary Approaches to Stop Hypertension) eating plan
        
        2. **Stay physically active**
           - Aim for at least 150 minutes of moderate exercise per week
           - Include both cardio and strength training
        
        3. **Maintain a healthy weight**
           - Even small amounts of weight loss can help lower blood pressure
        
        4. **Limit alcohol consumption**
           - No more than one drink per day for women
           - No more than two drinks per day for men
        
        5. **Don't smoke**
           - Smoking raises blood pressure and heart rate
        
        6. **Manage stress**
           - Practice relaxation techniques like deep breathing or meditation
           - Get enough sleep (7-8 hours per night)
        
        7. **Take medications as prescribed**
           - Never skip doses or stop medication without consulting your doctor
        
        8. **Monitor your blood pressure regularly**
           - Keep a log to share with your healthcare provider
        """
    }
