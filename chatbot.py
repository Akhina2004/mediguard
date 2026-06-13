import google.generativeai as genai
import os

# Get API key from environment variable
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    model = None


def get_chatbot_response(user_message):
    if not model:
        return "Chatbot not configured. Please set API key."
    
    try:
        prompt = f"""You are a helpful medical assistant chatbot for MediGuard app.
        Answer briefly and clearly. Always remind to consult a doctor for serious issues.
        
        User question: {user_message}
        
        Response (max 100 words):"""
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Sorry, I'm having trouble right now. Please try again. Error: {str(e)}"