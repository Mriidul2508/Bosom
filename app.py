import google.generativeai as genai
import datetime
import webbrowser
import os
import wikipedia
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import logging

# Setup simpler logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# async_mode='threading' is most stable for this setup
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=60)

def get_ai_reply(prompt, sid):
    """Runs in background to prevent blocking the server"""
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        socketio.emit('final_response', {'message': "Error: API Key missing."}, room=sid)
        return

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Simple, direct prompt
        response = model.generate_content(f"You are a helpful assistant. Reply in 2 sentences: {prompt}")
        
        if response.text:
            socketio.emit('final_response', {'message': response.text}, room=sid)
        else:
            socketio.emit('final_response', {'message': "I am not sure what to say."}, room=sid)
            
    except Exception as e:
        logger.error(f"AI Error: {e}")
        socketio.emit('final_response', {'message': "Sorry, my brain is offline right now."}, room=sid)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    emit('status_update', {'message': 'BOSOM Connected. Tap Mic.'})

@socketio.on('start_interaction')
def handle_interaction():
    # Simple greeting to confirm audio works
    hour = datetime.datetime.now().hour
    greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 18 else "Good Evening"
    emit('final_response', {'message': f"{greeting}, I am listening."})

@socketio.on('speech_recognized')
def handle_speech(data):
    query = data.get('query', '')
    if not query: 
        return

    # 1. Acknowledge immediately
    emit('user_speech', {'message': f"You: {query}"})
    emit('status_update', {'message': 'Thinking...'})

    # 2. Check simple commands first (Fast)
    if 'time' in query.lower():
        t = datetime.datetime.now().strftime("%I:%M %p")
        emit('final_response', {'message': f"It is {t}"})
        return
        
    elif 'wikipedia' in query.lower():
        try:
            q = query.lower().replace('wikipedia', '').strip()
            res = wikipedia.summary(q, sentences=1)
            emit('final_response', {'message': f"Wikipedia says: {res}"})
        except:
            emit('final_response', {'message': "I couldn't find that."})
        return

    # 3. If complex, run AI in BACKGROUND so connection doesn't drop
    from flask import request
    socketio.start_background_task(get_ai_reply, query, request.sid)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
