import os
import datetime
import logging
import base64
import wikipedia
from email.mime.text import MIMEText
import google.generativeai as genai
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# Google Auth Imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=90)

# --- CONFIGURATION ---
SCOPES = ['https://www.googleapis.com/auth/gmail.modify'] # Allows reading and sending

# --- GMAIL ENGINE ---
def get_gmail_service():
    """Authenticates and returns the Gmail Service"""
    creds = None
    # Load existing token if available
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If no valid token, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # NOTE: This flow requires a screen. Run locally to generate token.json first!
            if os.path.exists('credentials.json'):
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
                # Save the token for future use
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
            else:
                return None # No credentials setup
    
    return build('gmail', 'v1', credentials=creds)

def check_unread_emails():
    """Fetches top 3 unread emails"""
    service = get_gmail_service()
    if not service: return "I cannot access Gmail. Please configure credentials.json."

    try:
        # Request unread messages from Inbox
        results = service.users().messages().list(userId='me', labelIds=['UNREAD'], maxResults=3).execute()
        messages = results.get('messages', [])

        if not messages:
            return "You have no new emails."

        summary = "Here are your latest emails: "
        for msg in messages:
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = txt['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
            summary += f"From {sender.split('<')[0]}, Subject: {subject}. "
        
        return summary
    except Exception as e:
        logger.error(f"Gmail Read Error: {e}")
        return "I encountered an error reading your emails."

def send_email(to_address, subject, body):
    """Sends an email using Gmail API"""
    service = get_gmail_service()
    if not service: return "Gmail access not configured."

    try:
        message = MIMEText(body)
        message['to'] = to_address
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        return f"Email sent to {to_address}."
    except Exception as e:
        logger.error(f"Gmail Send Error: {e}")
        return "Failed to send the email."

# --- WIKIPEDIA ENGINE ---
def search_wikipedia(query):
    """Fetches summaries from Wikipedia"""
    try:
        # Clean query: remove command words like "who is", "tell me about"
        clean_query = query.replace("search wikipedia for", "").replace("who is", "").strip()
        summary = wikipedia.summary(clean_query, sentences=2)
        return f"According to Wikipedia: {summary}"
    except wikipedia.exceptions.DisambiguationError:
        return "There are multiple results for that. Please be more specific."
    except wikipedia.exceptions.PageError:
        return "I couldn't find a Wikipedia page for that."
    except Exception as e:
        return "Sorry, I couldn't access Wikipedia right now."

# --- AI ENGINE ---
def get_ai_response(text):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key: return "Error: API Key missing."
    genai.configure(api_key=api_key)
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        # We give the AI a "System Prompt" to act as an orchestrator
        prompt = f"""
        You are a smart assistant named BOSOM.
        User Input: "{text}"
        
        Rules:
        1. If the user asks to check emails, reply exactly: "ACTION: CHECK_EMAILS"
        2. If the user asks to send an email, reply in this format: "ACTION: SEND_EMAIL | recipient@example.com | Subject | Body"
        3. If the user asks for factual definitions or people, reply: "ACTION: WIKIPEDIA | [search_term]"
        4. Otherwise, answer the question normally in 1 sentence.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"I'm having trouble thinking: {e}"

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    emit('status_update', {'message': 'BOSOM Online. Ready.'})

@socketio.on('speech_recognized')
def handle_speech(data):
    query = data.get('query', '').strip()
    if not query: return
    
    emit('user_speech', {'message': f"You: {query}"})
    emit('status_update', {'message': 'Processing...'})

    response_text = ""
    
    # 1. Ask Gemini what to do
    ai_decision = get_ai_response(query)

    # 2. Router Logic
    if "ACTION: CHECK_EMAILS" in ai_decision:
        emit('status_update', {'message': 'Checking Inbox...'})
        response_text = check_unread_emails()
        
    elif "ACTION: SEND_EMAIL" in ai_decision:
        try:
            _, to, sub, body = ai_decision.split('|')
            emit('status_update', {'message': 'Sending Email...'})
            response_text = send_email(to.strip(), sub.strip(), body.strip())
        except:
            response_text = "I understood you want to send an email, but I missed the details. Please say 'Send email to [person] about [subject] saying [message]'"

    elif "ACTION: WIKIPEDIA" in ai_decision:
        topic = ai_decision.split('|')[1].strip()
        emit('status_update', {'message': f'Searching Wikipedia for {topic}...'})
        response_text = search_wikipedia(topic)

    else:
        # Normal conversation
        response_text = ai_decision

    # 3. Final Reply
    emit('final_response', {'message': response_text, 'should_listen': True})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
