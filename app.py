import os
import datetime
import logging
import time
import google.generativeai as genai
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# Threading mode for Render
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=90)

# --- AI ENGINE (HYBRID PRO/FLASH) ---
def get_ai_response(text):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key: return "Error: API Key missing."
    
    genai.configure(api_key=api_key)
    
    # 1. TRY THE SMART MODEL (2.5 PRO)
    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
        response = model.generate_content(f"Answer in 1 sentence: {text}")
        return response.text
    except Exception as e:
        error_msg = str(e)
        
        # 2. IF PRO FAILS (Rate Limit or Timeout), SWITCH TO FLASH
        logger.warning(f"Pro Model Failed ({error_msg}). Switching to Flash.")
        
        try:
            # Fallback to the faster, high-quota model
            fallback = genai.GenerativeModel('gemini-2.5-flash')
            response = fallback.generate_content(f"Answer in 1 sentence: {text}")
            return response.text
        except Exception as e2:
            if "429" in str(e2): return "RATE_LIMIT_HIT"
            return f"Error: {str(e2)}"

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    emit('status_update', {'message': 'System Online. Tap mic.'})

@socketio.on('start_interaction')
def handle_interaction():
    hour = datetime.datetime.now().hour
    if 0 <= hour < 12: greeting = "Good Morning!"
    elif 12 <= hour < 18: greeting = "Good Afternoon!"
    else: greeting = "Good Evening!"
    
    emit('final_response', {
        'message': greeting + " I am listening.",
        'should_listen': True 
    })

@socketio.on('speech_recognized')
def handle_speech(data):
    try:
        query = data.get('query', '').strip()
        
        # Noise Filter
        if not query or len(query) < 4:
            emit('status_update', {'message': 'Ignoring short noise...'})
            return 

        emit('user_speech', {'message': f"You: {query}"})
        emit('status_update', {'message': 'Thinking (Pro)...'})
        
        response_text = ""
        redirect_url = None
        should_listen = True 
        is_rate_limit = False

        if 'quit' in query.lower() or 'stop' in query.lower():
            response_text = "Goodbye!"
            should_listen = False
        
        elif 'open youtube' in query.lower():
            response_text = "Opening YouTube."
            redirect_url = "https://youtube.com"
            should_listen = False 
        
        elif 'time' in query.lower():
            t = datetime.datetime.now().strftime("%I:%M %p")
            response_text = f"The time is {t}"
        
        else:
            response_text = get_ai_response(query)
            if response_text == "RATE_LIMIT_HIT":
                response_text = "My brain is tired. Give me 10 seconds."
                is_rate_limit = True

        emit('final_response', {
            'message': response_text,
            'redirect': redirect_url,
            'should_listen': should_listen,
            'is_rate_limit': is_rate_limit
        })
        
    except Exception as e:
        logger.error(f"CRASH: {e}")
        emit('final_response', {'message': f"Error: {str(e)}", 'should_listen': False})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
