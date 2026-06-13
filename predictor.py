from sklearn.tree import DecisionTreeClassifier
from datetime import datetime
import numpy as np


def predict_adherence(user_meds):
    """
    Predict if user will take medicine based on history
    Returns: prediction percentage
    """
    
    if len(user_meds) < 3:
        return {
            "prediction": "Not enough data",
            "percentage": 0,
            "advice": "Add more medicines to get predictions"
        }
    
    try:
        # Prepare training data
        X = []  # Features: [hour, day_of_week, is_morning]
        y = []  # Labels: 1=taken, 0=missed
        
        for m in user_meds:
            if m.get("status") in ["taken", "missed"]:
                try:
                    # Parse time
                    time_obj = datetime.strptime(m["time"], "%I:%M %p")
                    hour = time_obj.hour
                    
                    # Parse date
                    date_obj = datetime.strptime(m["date"], "%Y-%m-%d")
                    day_of_week = date_obj.weekday()
                    
                    is_morning = 1 if hour < 12 else 0
                    
                    X.append([hour, day_of_week, is_morning])
                    y.append(1 if m["status"] == "taken" else 0)
                except:
                    continue
        
        if len(X) < 3:
            return {
                "prediction": "Need more data",
                "percentage": 0,
                "advice": "Mark medicines as taken/missed for better predictions"
            }
        
        # Train model
        model = DecisionTreeClassifier(max_depth=3)
        model.fit(X, y)
        
        # Calculate overall adherence
        taken_count = sum(y)
        total_count = len(y)
        percentage = round((taken_count / total_count) * 100, 1)
        
        # Generate advice
        if percentage >= 80:
            advice = "🌟 Excellent! Keep up the good work!"
            prediction = "High adherence"
        elif percentage >= 60:
            advice = "👍 Good. Try to be more consistent."
            prediction = "Moderate adherence"
        elif percentage >= 40:
            advice = "⚠️ Need improvement. Set more reminders."
            prediction = "Low adherence"
        else:
            advice = "🚨 Critical! Please take medicines regularly."
            prediction = "Very low adherence"
        
        return {
            "prediction": prediction,
            "percentage": percentage,
            "advice": advice
        }
    
    except Exception as e:
        return {
            "prediction": "Error",
            "percentage": 0,
            "advice": f"Could not predict: {str(e)}"
        }


def get_insights(user_meds):
    """
    Generate smart insights from medicine data
    """
    insights = []
    
    if not user_meds:
        return ["Add medicines to see insights"]
    
    # Total stats
    total = len(user_meds)
    taken = sum(1 for m in user_meds if m.get("status") == "taken")
    missed = sum(1 for m in user_meds if m.get("status") == "missed")
    
    # Best time analysis
    morning_taken = sum(1 for m in user_meds 
                       if m.get("status") == "taken" 
                       and "AM" in m.get("time", ""))
    evening_taken = sum(1 for m in user_meds 
                       if m.get("status") == "taken" 
                       and "PM" in m.get("time", ""))
    
    if morning_taken > evening_taken:
        insights.append(f"☀️ You're more consistent in the morning ({morning_taken} taken)")
    elif evening_taken > morning_taken:
        insights.append(f"🌙 You're more consistent in the evening ({evening_taken} taken)")
    
    # Missed pattern
    if missed > 0:
        miss_rate = round((missed / total) * 100, 1)
        insights.append(f"⚠️ You miss {miss_rate}% of your medicines")
    
    # Streak
    if taken >= 5:
        insights.append(f"🔥 Great! You've taken {taken} medicines so far!")
    
    # Recurring
    recurring = sum(1 for m in user_meds if m.get("recurring") == "daily")
    if recurring > 0:
        insights.append(f"🔁 You have {recurring} daily recurring medicines")
    
    if not insights:
        insights.append("📊 Keep tracking to see more insights!")
    
    return insights