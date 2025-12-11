import os
import datetime
import logging
# import webbrowser  <-- DELETED: This was killing your server
import google.generativeai as genai
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# 1. Setup Logging so you can see errors in Render Dashboard
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# 2. CONFIGURATION FOR STABILITY
# async_mode='threading' prevents the "Invalid Session" error on Render
# ping_timeout=90 gives the connection more time before failing
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=90)

# --- AI ENGINE ---
def get_ai_response(text):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key: 
        return "Error: Gemini API Key is missing."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Keep it short to prevent timeouts
        response = model.generate_content(f"Answer in 1 sentence: {text}")
        return response.text
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return f"I'm having trouble thinking: {str(e)}"

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

        # 2. SAFE COMMAND LOGIC (No crashes)
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
