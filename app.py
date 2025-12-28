import os
import datetime
import logging
import base64
import json
import wikipedia
from email.mime.text import MIMEText
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

# Google Auth Imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['UPLOAD_FOLDER'] = '.' # Save credentials in current folder

# Threading mode for Render stability
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=90)

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# --- GMAIL AUTH FLOW (HEADLESS SERVER SUPPORT) ---
def get_gmail_service():
    """Returns Gmail Service or None if not authenticated"""
    creds = None
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except:
            os.remove('token.json') # Delete corrupted token
            return None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
            except:
                return None # Refresh failed
        else:
            return None # Needs fresh login
            
    return build('gmail', 'v1', credentials=creds)

@app.route('/upload_credentials', methods=['POST'])
def upload_credentials():
    """Step 1: User uploads credentials.json"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})

    if file:
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'credentials.json'))
        
        # Initiate Auth Flow immediately
        try:
            flow = Flow.from_client_secrets_file(
                'credentials.json',
                scopes=SCOPES,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob' # Special redirect for copy-paste flow
            )
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            # Send URL back to frontend so user can click it
            return jsonify({'success': True, 'auth_url': auth_url})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

@socketio.on('submit_auth_code')
def handle_auth_code(data):
    """Step 2: User pastes the Google Auth Code"""
    code = data.get('code')
    try:
        flow = Flow.from_client_secrets_file(
            'credentials.json',
            scopes=SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Save the permanent token
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
        emit('status_update', {'message': 'Gmail Connected Successfully!'})
        emit('gmail_status', {'connected': True})
    except Exception as e:
        emit('status_update', {'message': f'Auth Failed: {str(e)}'})

# --- GMAIL FUNCTIONS ---
def check_unread_emails():
    service = get_gmail_service()
    if not service: return "Gmail not connected. Please upload credentials."

    try:
        results = service.users().messages().list(userId='me', labelIds=['UNREAD'], maxResults=3).execute()
        messages = results.get('messages', [])

        if not messages: return "You have no new emails."

        summary = "Here are your latest emails: "
        for msg in messages:
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = txt['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
            # Clean sender name
            sender_name = sender.split('<')[0].strip().replace('"', '')
            summary += f"From {sender_name}, Subject: {subject}. "
        return summary
    except Exception as e:
        logger.error(f"Gmail Read Error: {e}")
        return "Error reading emails."

def send_email(to_address, subject, body):
    service = get_gmail_service()
    if not service: return "Gmail not connected."

    try:
        message = MIMEText(body)
        message['to'] = to_address
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        return f"Email sent to {to_address}."
    except Exception as e:
        return f"Failed to send email: {e}"

# --- AI ENGINE ---
def get_ai_response(text):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key: return "Error: API Key missing."
    genai.configure(api_key=api_key)
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        # Instruct AI to route commands
        prompt = f"""
        You are BOSOM, an advanced AI assistant.
        User: "{text}"
        
        If user wants to check email -> Reply: "ACTION: CHECK_EMAILS"
        If user wants to send email -> Reply: "ACTION: SEND_EMAIL | to@email.com | Subject | Body"
        If user asks for facts/definitions -> Reply: "ACTION: WIKIPEDIA | Search Term"
        Otherwise -> Reply naturally in 1 sentence.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error: {e}"

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    # Check if Gmail is already ready
    is_connected = os.path.exists('token.json')
    emit('gmail_status', {'connected': is_connected})
    emit('status_update', {'message': 'System Online.'})

@socketio.on('speech_recognized')
def handle_speech(data):
    query = data.get('query', '').strip()
    if not query: return
    
    emit('user_speech', {'message': f"You: {query}"})
    emit('status_update', {'message': 'Processing...'})

    response_text = ""
    
    # 1. AI Decision
    ai_decision = get_ai_response(query)

    # 2. Execution
    if "ACTION: CHECK_EMAILS" in ai_decision:
        emit('status_update', {'message': 'Scanning Inbox...'})
        response_text = check_unread_emails()
        
    elif "ACTION: SEND_EMAIL" in ai_decision:
        try:
            parts = ai_decision.split('|')
            to, sub, body = parts[1].strip(), parts[2].strip(), parts[3].strip()
            emit('status_update', {'message': 'Sending Email...'})
            response_text = send_email(to, sub, body)
        except:
            response_text = "I couldn't get the email details. Please try again."

    elif "ACTION: WIKIPEDIA" in ai_decision:
        try:
            topic = ai_decision.split('|')[1].strip()
            emit('status_update', {'message': f'Searching Wiki for {topic}...'})
            response_text = wikipedia.summary(topic, sentences=2)
        except:
            response_text = "I couldn't find that on Wikipedia."

    else:
        response_text = ai_decision

    emit('final_response', {'message': response_text, 'should_listen': True})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
