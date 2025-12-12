import os
import datetime
import logging
import base64
import google.generativeai as genai
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# Threading mode for stability
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=90)

# --- AI HELPERS ---
def get_text_response(text):
    """Standard Text-to-Text for Android/PC"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key: return "Error: API Key missing."
    genai.configure(api_key=api_key)
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(f"Answer in 1 sentence: {text}")
        return response.text
    except:
        # Fallback
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(f"Answer in 1 sentence: {text}")
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

def get_audio_response(audio_bytes, mime_type):
    """Audio-to-Text for iOS"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key: return "Error: API Key missing."
    genai.configure(api_key=api_key)

    try:
        model = genai.GenerativeModel('gemini-2.5-flash') # 2.5 handles audio reliably
        
        # Send raw audio directly to Gemini
        response = model.generate_content([
            {'mime_type': mime_type, 'data': base64.b64encode(audio_bytes).decode('utf-8')},
            "Listen to this audio. If it is a command like 'time' or 'open youtube', execute it by saying just the command words. Otherwise, answer the question in 1 sentence."
        ])
        return response.text
    except Exception as e:
        logger.error(f"Audio Error: {e}")
        return "I couldn't hear that clearly."

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    emit('status_update', {'message': 'System Online. Tap mic.'})

@socketio.on('start_interaction')
def handle_interaction():
    # Only for greeting
    h = datetime.datetime.now().hour
    greet = "Good Morning" if h < 12 else "Good Afternoon" if h < 18 else "Good Evening"
    emit('final_response', {'message': f"{greet}, ready.", 'should_listen': True})

# --- ANDROID/PC HANDLER (Text) ---
@socketio.on('speech_recognized')
def handle_speech(data):
    process_response(data.get('query', ''), is_audio=False)

# --- iOS HANDLER (Audio) ---
@socketio.on('process_audio')
def handle_audio(data):
    audio_blob = data.get('audio')
    mime = data.get('mime', 'audio/webm')
    
    emit('status_update', {'message': 'Processing Audio...'})
    
    # 1. Let Gemini convert Audio -> Text/Response
    response_text = get_audio_response(audio_blob, mime)
    
    # 2. Process logic (Time, Youtube, etc)
    # We pass the AI's response as the "Query" to check for commands
    process_response(response_text, is_audio=True)

def process_response(query, is_audio):
    if not query: return
    
    # Clean query
    query = query.strip()
    
    # If audio, we don't need to repeat "You said...", just show the answer
    if not is_audio:
        emit('user_speech', {'message': f"You: {query}"})
    
    emit('status_update', {'message': 'Thinking...'})

    response_text = ""
    redirect_url = None
    should_listen = True

    q_lower = query.lower()

    # COMMANDS
    if 'quit' in q_lower or 'stop' in q_lower:
        response_text = "Goodbye!"
        should_listen = False
    elif 'open youtube' in q_lower:
        response_text = "Opening YouTube."
        redirect_url = "https://youtube.com"
        should_listen = False
    elif 'time' in q_lower:
        t = datetime.datetime.now().strftime("%I:%M %p")
        response_text = f"The time is {t}"
    else:
        # If it was audio, 'query' is ALREADY the AI response.
        if is_audio:
            response_text = query
        else:
            response_text = get_text_response(query)

    emit('final_response', {
        'message': response_text,
        'redirect': redirect_url,
        'should_listen': should_listen
    })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
