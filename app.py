import os
import datetime
import logging
import google.generativeai as genai
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# Threading mode prevents "Invalid Session" errors
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=90)

# --- AI ENGINE ---
def get_ai_response(text):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key: 
        return "Error: Gemini API Key is missing."
    try:
        genai.configure(api_key=api_key)
        
        # Switched to 'gemini-1.5-flash-latest' for better compatibility
        # If this fails, the code catches it below.
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        response = model.generate_content(f"Answer in 1 sentence: {text}")
        return response.text
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        # Detailed error for debugging
        if "404" in str(e):
            return "Error: Server library is old. Please update requirements.txt to 'google-generativeai>=0.7.2'"
        return f"My brain had a glitch: {str(e)}"

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    emit('status_update', {'message': 'System Online. Tap mic.'})

@socketio.on('start_interaction')
def handle_interaction():
    emit('status_update', {'message': 'Listening...'})

@socketio.on('speech_recognized')
def handle_speech(data):
    try:
        query = data.get('query', '').lower()
        if not query: return

        # 1. Immediate Feedback
        emit('user_speech', {'message': f"You: {query}"})
        emit('status_update', {'message': 'Processing...'})
        
        response_text = ""
        redirect_url = None

        # 2. COMMAND LOGIC
        if 'open youtube' in query:
            response_text = "Opening YouTube..."
            redirect_url = "https://youtube.com"
        
        elif 'open google' in query:
            response_text = "Opening Google..."
            redirect_url = "https://google.com"

        elif 'time' in query:
            t = datetime.datetime.now().strftime("%I:%M %p")
            response_text = f"The time is {t}"
        
        else:
            # AI Fallback
            response_text = get_ai_response(query)

        # 3. SEND RESULT
        emit('final_response', {
            'message': response_text,
            'redirect': redirect_url
        })
        
    except Exception as e:
        logger.error(f"CRASH: {e}")
        emit('final_response', {'message': f"Error: {str(e)}"})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
