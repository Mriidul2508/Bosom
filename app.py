import google.generativeai as genai
import datetime
import os
import wikipedia
import logging
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# Threading mode is best for Render
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=60)

# --- GEMINI SETUP ---
def get_ai_reply(prompt):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return "Error: API Key is missing on the server."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(f"Reply in 1 sentence: {prompt}")
        return response.text if response.text else "I'm not sure."
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return "I'm having trouble connecting to my brain."

# --- MAIN LOGIC ---
@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    emit('status_update', {'message': 'Online and Ready.'})

@socketio.on('start_interaction')
def handle_interaction():
    # Just a sound check, don't trigger AI yet
    emit('status_update', {'message': 'Listening...'})

@socketio.on('speech_recognized')
def handle_speech(data):
    query = data.get('query', '').lower()
    if not query: return

    logger.info(f"User said: {query}")
    
    # 1. Update Chat UI immediately
    emit('user_speech', {'message': f"You: {query}"})
    emit('status_update', {'message': 'Thinking...'})

    response_text = ""
    redirect_url = None

    # 2. COMMANDS
    if 'open youtube' in query:
        response_text = "Opening YouTube for you."
        redirect_url = "https://youtube.com"
        
    elif 'open google' in query:
        response_text = "Opening Google."
        redirect_url = "https://google.com"

    elif 'time' in query:
        t = datetime.datetime.now().strftime("%I:%M %p")
        response_text = f"It is {t}"

    elif 'wikipedia' in query:
        try:
            q = query.replace('wikipedia', '').strip()
            response_text = wikipedia.summary(q, sentences=1)
        except:
            response_text = "I couldn't find that on Wikipedia."
            
    else:
        # 3. AI FALLBACK
        response_text = get_ai_reply(query)

    # 4. SEND RESPONSE TO FRONTEND
    emit('final_response', {
        'message': response_text,
        'redirect': redirect_url 
    })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
