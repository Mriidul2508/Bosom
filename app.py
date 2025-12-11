import os
import datetime
import logging
import google.generativeai as genai
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# 1. Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# 2. Threading for Render Stability
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=90)

# --- DIAGNOSTIC: PRINT AVAILABLE MODELS ON STARTUP ---
def print_available_models():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("STARTUP ERROR: API Key is missing.")
        return
    try:
        genai.configure(api_key=api_key)
        logger.info("--- CHECKING AVAILABLE MODELS ---")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                logger.info(f"Found Model: {m.name}")
        logger.info("--- END MODEL CHECK ---")
    except Exception as e:
        logger.error(f"STARTUP ERROR: Could not list models. {e}")

# Run the check immediately
print_available_models()

# --- AI ENGINE ---
def get_ai_response(text):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key: 
        return "Error: Gemini API Key is missing."
    try:
        genai.configure(api_key=api_key)
        
        # FIXED: Reverted to the standard, stable ID
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        response = model.generate_content(f"Answer in 1 sentence: {text}")
        return response.text
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return f"Error: {str(e)}"

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
