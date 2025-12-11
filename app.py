import google.generativeai as genai
import datetime
import webbrowser
import os
import wikipedia
import cv2
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import logging
import time

# Suppress logs
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GRPC_LOG_SEVERITY_LEVEL'] = 'ERROR'

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# --- REVISION 2: Use 'threading' async_mode for compatibility ---
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

def wishMe():
    hour = int(datetime.datetime.now().hour)
    if 0 <= hour < 12:
        return "Good Morning! I'm BOSOM, your AI assistant."
    elif 12 <= hour < 18:
        return "Good Afternoon! I'm BOSOM, ready to help."
    else:
        return "Good Evening! BOSOM here to assist."

def get_gemini_response(prompt):
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key or api_key == "YOUR_GEMINI_API_KEY":
        socketio.emit('final_response', {'message': "BOSOM: Gemini API key not configured."})
        print("Error: GEMINI_API_KEY is missing in Environment Variables.")
        return

    try:
        genai.configure(api_key=api_key)
        
        # --- REVISION 3: Updated to valid model name (1.5-flash) ---
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        modified_prompt = f"{prompt} Please keep your answer under 50 words."
        response_stream = model.generate_content(modified_prompt, stream=True)
        
        full_response = ""
        for chunk in response_stream:
            if chunk.text:
                full_response += chunk.text
                socketio.emit('stream_response_chunk', {'chunk': chunk.text})
        
        socketio.emit('stream_end', {'full_message': full_response})
    except Exception as e:
        # Print actual error to Render logs for debugging
        print(f"Gemini Error: {e}")
        socketio.emit('final_response', {'message': "BOSOM: Sorry, trouble connecting to my brain."})

def process_query(query):
    query_lower = query.lower()

    if 'wikipedia' in query_lower:
        socketio.emit('status_update', {'message': 'BOSOM is searching Wikipedia...'})
        try:
            query_lower = query_lower.replace("wikipedia", "").strip()
            results = wikipedia.summary(query_lower, sentences=2)
            return f"BOSOM: According to Wikipedia, {results}"
        except wikipedia.exceptions.PageError:
            return f"BOSOM: Sorry, no Wikipedia page for {query_lower}."
        except wikipedia.exceptions.DisambiguationError:
            return "BOSOM: Multiple results. Be more specific."
        except Exception as e:
            print(f"Wikipedia Error: {e}")
            return "BOSOM: Couldn't fetch from Wikipedia."

    elif 'open youtube' in query_lower:
        # Note: This opens on the SERVER, not the user's browser, when deployed.
        # To fix this, you'd handle it in Javascript on the frontend.
        webbrowser.open("https://youtube.com")
        return "BOSOM: Requesting to open YouTube..."

    elif 'open google' in query_lower:
        webbrowser.open("https://google.com")
        return "BOSOM: Requesting to open Google..."
        
    elif 'play music' in query_lower:
        # --- REVISION 4: Prevent crash on Linux/Render ---
        if os.name == 'nt': # Checks if running on Windows
            music_dir = 'C:\\Users\\YourUser\\Music'
            if os.path.exists(music_dir):
                os.startfile(music_dir)
                return "BOSOM: Opening your music folder."
            else:
                return "BOSOM: Music directory not found."
        else:
            return "BOSOM: I cannot open local folders on a cloud server."

    elif 'the time' in query_lower:
        strTime = datetime.datetime.now().strftime("%I:%M %p")
        return f"BOSOM: The time is {strTime}"

    elif 'open camera' in query_lower:
        # --- REVISION 5: Prevent crash on Headless Server ---
        # cv2.imshow requires a screen. Render is a headless server.
        # We catch this to prevent the app from restarting/crashing.
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return "BOSOM: No camera found on server."
            
            # Read one frame to check connection, but DON'T show window
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                return "BOSOM: Camera connected (Server-side), but I cannot display it here."
            else:
                return "BOSOM: Could not access the camera."
        except Exception as e:
            print(f"Camera Error: {e}")
            return "BOSOM: Camera features are disabled on the cloud."

    elif 'quit' in query_lower or 'exit' in query_lower or 'stop listening' in query_lower:
        global continuous_mode
        continuous_mode = False
        return "BOSOM: Goodbye! Listening stopped."

    else:
        get_gemini_response(query)
        return None

@app.route('/')
def index():
    return render_template('index.html')

continuous_mode = True

@socketio.on('connect')
def handle_connect():
    greeting = wishMe()
    emit('final_response', {'message': greeting})
    if continuous_mode:
        socketio.emit('status_update', {'message': 'BOSOM: Continuous mode active. Listening...'})
        socketio.emit('start_listening')

@socketio.on('speech_recognized')
def handle_speech_recognized(data):
    query = data.get('query', '')
    if not query:
        return
    
    socketio.emit('user_speech', {'message': f'You said: "{query}"'})
    socketio.emit('status_update', {'message': 'BOSOM: Thinking...'})
    
    response = process_query(query)
    if response is not None:
        socketio.emit('final_response', {'message': response})
        if continuous_mode:
            socketio.emit('start_listening')
    else:
        pass

if __name__ == '__main__':
    # allow_unsafe_werkzeug is okay for dev/demos
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), allow_unsafe_werkzeug=True)
