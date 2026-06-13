import google.generativeai as genai

# Configure Gemini
GEMINI_API_KEY = "AQ.Ab8RN6KFtPwshPaUrBn4RzWsG5WY8u1iUAu7KRZ1145bZm3Chw"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')


def get_chatbot_response(user_message):
    try:
        # Medical context prompt
        prompt = f"""You are a helpful medical assistant chatbot for MediGuard app.
        Answer briefly and clearly. Always remind to consult a doctor for serious issues.
        
        User question: {user_message}
        
        Response (max 100 words):"""
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Sorry, I'm having trouble right now. Please try again. Error: {str(e)}"