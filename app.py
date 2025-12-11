import google.generativeai as genai
import datetime
import webbrowser
import os
import wikipedia
import cv2
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import logging

# Suppress logs
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GRPC_LOG_SEVERITY_LEVEL'] = 'ERROR'
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
# Use threading for stability on Render
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- CONFIGURATION ---
# Set this to False to fix the "Listening loop" and browser blocking issues
continuous_mode = False 

def wishMe():
    hour = int(datetime.datetime.now().hour)
    if 0 <= hour < 12:
        return "Good Morning! I'm BOSOM."
    elif 12 <= hour < 18:
        return "Good Afternoon! I'm BOSOM."
    else:
        return "Good Evening! I'm BOSOM."

def get_gemini_response(prompt):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        socketio.emit('final_response', {'message': "BOSOM: API key missing."})
        return

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        modified_prompt = f"{prompt} Keep answer under 50 words."
        
        # Using non-streaming for stability with SocketIO threading
        response = model.generate_content(modified_prompt)
        if response.text:
            socketio.emit('final_response', {'message': response.text})
            
    except Exception as e:
        print(f"Gemini Error: {e}")
        socketio.emit('final_response', {'message': "BOSOM: Brain connection error."})

def process_query(query):
    query_lower = query.lower()

    if 'wikipedia' in query_lower:
        try:
            query_lower = query_lower.replace("wikipedia", "").strip()
            results = wikipedia.summary(query_lower, sentences=2)
            return f"According to Wikipedia, {results}"
        except:
            return "Could not search Wikipedia."

    elif 'open youtube' in query_lower:
        # Note: This opens on SERVER side if deployed. 
        # Ideally handle in frontend JS.
        webbrowser.open("https://youtube.com") 
        return "Opening YouTube."

    elif 'open google' in query_lower:
        webbrowser.open("https://google.com")
        return "Opening Google."
        
    elif 'time' in query_lower:
        strTime = datetime.datetime.now().strftime("%I:%M %p")
        return f"The time is {strTime}"
        
    # --- FIX: Removed Camera/Music to prevent server crashes ---
    
    else:
        get_gemini_response(query)
        return None

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    # We do NOT trigger audio/listening here anymore.
    # Just send a text status update.
    print("Client connected")
    emit('status_update', {'message': 'BOSOM is online. Click Mic to speak.'})

@socketio.on('start_interaction')
def handle_interaction():
    # Triggered only when user clicks the button
    greeting = wishMe()
    emit('final_response', {'message': greeting})
    # We tell frontend to listen AFTER the greeting
    emit('start_listening_command')

@socketio.on('speech_recognized')
def handle_speech_recognized(data):
    query = data.get('query', '')
    if not query:
        return
    
    socketio.emit('user_speech', {'message': f'You: {query}'})
    socketio.emit('status_update', {'message': 'Thinking...'})
    
    response = process_query(query)
    
    if response:
        socketio.emit('final_response', {'message': response})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), allow_unsafe_werkzeug=True)
