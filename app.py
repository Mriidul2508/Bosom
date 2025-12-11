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

# Threading mode for Render stability
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=90)

# --- AI ENGINE ---
def get_ai_response(text):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key: return "Error: API Key missing."
    
    genai.configure(api_key=api_key)
    
    # REQUESTED MODEL: gemini-2.5-flash
    model_name = 'gemini-2.5-flash'
    
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(f"Answer in 1 sentence: {text}")
        return response.text
    except Exception as e:
        # Fallback if 2.5 is not available yet
        logger.warning(f"Gemini 2.5 Error: {e}. Falling back to 1.5-flash.")
        try:
            fallback_model = genai.GenerativeModel('gemini-1.5-flash')
            response = fallback_model.generate_content(f"Answer in 1 sentence: {text}")
            return response.text
        except Exception as e2:
            return f"Error: {str(e2)}"

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    emit('status_update', {'message': 'System Online. Tap mic to start.'})

@socketio.on('start_interaction')
def handle_interaction():
    # 1. GREETING
    hour = datetime.datetime.now().hour
    if 0 <= hour < 12: greeting = "Good Morning!"
    elif 12 <= hour < 18: greeting = "Good Afternoon!"
    else: greeting = "Good Evening!"
    
    greeting += " I am listening."

    # 2. SEND GREETING + START LISTENING LOOP
    emit('final_response', {
        'message': greeting,
        'should_listen': True 
    })

@socketio.on('speech_recognized')
def handle_speech(data):
    try:
        query = data.get('query', '').lower()
        if not query: return

        # SEND CONFIRMATION (The only one that will show in chat)
        emit('user_speech', {'message': f"You: {query}"})
        emit('status_update', {'message': 'Thinking...'})
        
        response_text = ""
        redirect_url = None
        should_listen = True 

        # --- LOGIC ---
        if 'quit' in query or 'exit' in query or 'stop' in query:
            response_text = "Goodbye! Have a great day."
            should_listen = False
        
        elif 'open youtube' in query:
            response_text = "Opening YouTube."
            redirect_url = "https://youtube.com"
            should_listen = False 
        
        elif 'open google' in query:
            response_text = "Opening Google."
            redirect_url = "https://google.com"
            should_listen = False

        elif 'time' in query:
            t = datetime.datetime.now().strftime("%I:%M %p")
            response_text = f"The time is {t}"
        
        else:
            response_text = get_ai_response(query)

        # --- SEND RESPONSE ---
        emit('final_response', {
            'message': response_text,
            'redirect': redirect_url,
            'should_listen': should_listen
        })
        
    except Exception as e:
        logger.error(f"CRASH: {e}")
        emit('final_response', {'message': f"Error: {str(e)}", 'should_listen': False})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
