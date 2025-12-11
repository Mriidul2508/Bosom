import google.generativeai as genai
import datetime
import webbrowser
import os
import wikipedia
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import logging

# 1. Setup Logging to see errors in Render Dashboard
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 2. Increase ping timeout to prevent disconnects while AI thinks
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=60)

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
    
    # Check if API Key exists
    if not api_key:
        logger.error("API Key Missing")
        socketio.emit('final_response', {'message': "Error: Gemini API Key is missing on Server."})
        return

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 3. Add Safety Settings to prevent blocking harmless queries
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]

        modified_prompt = f"You are a helpful voice assistant named BOSOM. Answer this briefly in under 40 words: {prompt}"
        
        # Generate content
        response = model.generate_content(modified_prompt, safety_settings=safety_settings)

        # 4. safely access text (Prevent crash if blocked)
        if response.candidates and response.candidates[0].content.parts:
            reply_text = response.text
            socketio.emit('final_response', {'message': reply_text})
        else:
            socketio.emit('final_response', {'message': "I heard you, but I couldn't think of a response."})

    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        # Send the actual error to the frontend so you can see it
        socketio.emit('final_response', {'message': f"System Error: {str(e)}"})

def process_query(query):
    query_lower = query.lower()

    if 'wikipedia' in query_lower:
        try:
            query_lower = query_lower.replace("wikipedia", "").strip()
            results = wikipedia.summary(query_lower, sentences=2)
            return f"According to Wikipedia, {results}"
        except:
            return "Could not find that on Wikipedia."

    elif 'open youtube' in query_lower:
        return "I cannot open tabs on your phone, but I can search for you."

    elif 'time' in query_lower:
        strTime = datetime.datetime.now().strftime("%I:%M %p")
        return f"The time is {strTime}"

    else:
        # Pass to Gemini
        get_gemini_response(query)
        return None

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    logger.info("Client connected")
    emit('status_update', {'message': 'BOSOM is online. Tap mic to speak.'})

@socketio.on('start_interaction')
def handle_interaction():
    # Only greet, do NOT auto-listen (improves stability)
    greeting = wishMe()
    emit('final_response', {'message': greeting})

@socketio.on('speech_recognized')
def handle_speech_recognized(data):
    query = data.get('query', '')
    logger.info(f"Received query: {query}")
    
    if not query:
        return
    
    # 5. Send immediate feedback that we heard the user
    socketio.emit('user_speech', {'message': f'You: {query}'})
    socketio.emit('status_update', {'message': 'Thinking...'})
    
    # Process
    response = process_query(query)
    
    # If it was a simple command (Time/Wiki), reply immediately
    if response:
        socketio.emit('final_response', {'message': response})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), allow_unsafe_werkzeug=True)
