import speech_recognition as sr
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
socketio = SocketIO(app, cors_allowed_origins="*")

# Removed pyttsx3 engine and speak function (TTS is browser-based)

def wishMe():
    hour = int(datetime.datetime.now().hour)
    if 0 <= hour < 12:
        return "Good Morning! I'm BOSOM, your AI assistant."
    elif 12 <= hour < 18:
        return "Good Afternoon! I'm BOSOM, ready to help."
    else:
        return "Good Evening! BOSOM here to assist."

def get_gemini_response(prompt):
    api_key = os.getenv('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY')  # Use env var for security
    if not api_key or api_key == "YOUR_GEMINI_API_KEY":
        socketio.emit('final_response', {'message': "BOSOM: Gemini API key not configured."})
        return

    try:
        genai.configure(api_key=api_key)
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
        webbrowser.open("https://youtube.com")
        return "BOSOM: Opening YouTube..."

    elif 'open google' in query_lower:
        webbrowser.open("https://google.com")
        return "BOSOM: Opening Google..."
        
    elif 'play music' in query_lower:
        music_dir = 'C:\\Users\\YourUser\\Music'  # Update to your local path; on cloud, this won't work
        if os.path.exists(music_dir):
            os.startfile(music_dir)
            return "BOSOM: Opening your music folder."
        else:
            return "BOSOM: Music directory not found. Update the path in the code."

    elif 'the time' in query_lower:
        strTime = datetime.datetime.now().strftime("%I:%M %p")
        return f"BOSOM: The time is {strTime}"

    elif 'open camera' in query_lower:
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return "BOSOM: Could not open camera."
            ret, frame = cap.read()
            if ret:
                cv2.imshow('Camera', frame)
                cv2.waitKey(2000)
            cap.release()
            cv2.destroyAllWindows()
            return "BOSOM: Opening camera for a moment."
        except Exception as e:
            print(f"Camera Error: {e}")
            return "BOSOM: Could not access the camera."
            
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

listening_in_progress = False
continuous_mode = True

@socketio.on('connect')
def handle_connect():
    greeting = wishMe()
    emit('final_response', {'message': greeting})
    if continuous_mode:
        socketio.emit('status_update', {'message': 'BOSOM: Continuous mode active. Listening...'})
        time.sleep(1)
        handle_listen_command({})

@socketio.on('listen_command')
def handle_listen_command(json):
    global listening_in_progress, continuous_mode
    if not continuous_mode or listening_in_progress:
        return
    listening_in_progress = True
    
    socketio.emit('status_update', {'message': 'BOSOM: Listening...'})
    
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.pause_threshold = 1
        r.adjust_for_ambient_noise(source)
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
            socketio.emit('status_update', {'message': 'BOSOM: Recognizing...'})
            query = r.recognize_google(audio, language='en-in')
            socketio.emit('user_speech', {'message': f'You said: "{query}"'})
            socketio.emit('status_update', {'message': 'BOSOM: Thinking...'})
            
            response = process_query(query)
            if response is not None:
                socketio.emit('final_response', {'message': response})
        except sr.WaitTimeoutError:
            socketio.emit('status_update', {'message': "BOSOM: No speech detected. Retrying..."})
            time.sleep(1)
            if continuous_mode:
                handle_listen_command({})
        except sr.UnknownValueError:
            socketio.emit('status_update', {'message': "BOSOM: Didn't understand. Retrying..."})
            time.sleep(1)
            if continuous_mode:
                handle_listen_command({})
        except sr.RequestError as e:
            socketio.emit('final_response', {'message': f"BOSOM: Request error: {e}"})
        except Exception as e:
            print(f"Error: {e}")
            socketio.emit('final_response', {'message': "BOSOM: Unexpected error."})
        finally:
            listening_in_progress = False

if __name__ == '__main__':
    print("Starting BOSOM AI server...")
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
