import whisper
import queue, threading, time
import numpy as np
from scipy.io.wavfile import write as wv
import tempfile, os
import sounddevice as sd
import pyttsx3
from datetime import datetime 
import pickle 
import face_recognition
import cv2
from pathlib import Path 
import google.generativeai as genai
from dotenv import load_dotenv
import requests, json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

class AIGuardAgent:
    def __init__(self):
        self.model = whisper.load_model("base.en")
        self.SAMPLE_RATE = 16000
        self.CHUNK_SECONDS = 2
        self.audio_queue = queue.Queue(maxsize=10)
        
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)
        
        self.guard_mode = False
        self.listening = False
        self.stop_flag = False
        self.alarm_activated = False
        
        self.face_db_path = "face_database.pkl"
        self.ensure_face_db_directory()
        self.load_trusted_faces()
        
        # FIXED: Better camera management
        self.camera = None
        self.camera_lock = threading.Lock()
        self.camera_in_use = False
        self.current_camera_thread = None


        # Thread safety
        self.thread_lock = threading.Lock()
        self.camera = None
        self.camera_lock = threading.Lock()
        
        # NEW: Authority notification settings
        self.authority_contacts = ["security@campus.edu"]
        self.webhook_url = "https://hooks.example.com/alert"
        
        # Face tracking
        self.unknown_person_tracker = {}
        self.conversation_memory = {}
        self.situation_context = {
            "time_of_day": "",
            "last_recognized_person": "",
            "recent_events": []
        }
        
        self.escalation_levels = {
            1: "polite warning",
            2: "firm warning", 
            3: "final warning"
        }
        
        self.activation_phrases = [
            "guard my room", "protect my room", "secure my room", 
            "start guard mode", "activate guard"
        ]
        
        self.deactivation_phrases = [
            "stop guard mode", "deactivate guard", "stand down",
            "stop monitoring", "goodbye guard"
        ]
        
        self.enrollment_phrases = [
            "enroll face", "register face", "add trusted person"
        ]
        
        self.current_dialog_context = ""
        self.setup_llm()

    # Email configuration
        self.email_config = {
            'smtp_server': 'smtp.gmail.com',  # or your email provider
            'smtp_port': 587,
            'sender_email': 'your_email@gmail.com',  # Configure this
            'sender_password': 'your_app_password',  # Gmail app password
            'receiver_emails': ['security@campus.edu', 'your_phone@vtext.com']  # Verizon: number@vtext.com
        }
        
        # Webhook configuration
        self.webhook_urls = [
            "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",  # Slack webhook
            "https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK"  # Discord webhook
        ]
        
        # Load from environment variables (more secure)
        self._load_notification_config()
    ####################################
    #      RESOURCE MANAGEMENT         #
    ####################################    
    def _load_notification_config(self):
        """Load notification config from environment variables"""
        import os
        # Email config
        self.email_config['sender_email'] = os.getenv('GUARD_EMAIL', 'your_email@gmail.com')
        self.email_config['sender_password'] = os.getenv('GUARD_EMAIL_PASSWORD', '')
        
        # Webhook URLs from environment
        webhook_env = os.getenv('GUARD_WEBHOOKS', '')
        if webhook_env:
            self.webhook_urls = webhook_env.split(',')
        
        print(f"Notification system configured for {self.email_config['sender_email']}")
    def send_alert_email(self, subject, message):
        """Send actual email alert"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['sender_email']
            msg['To'] = ', '.join(self.email_config['receiver_emails'])
            msg['Subject'] = subject
            
            body = f"""
            AI GUARD ALERT
            
            {message}
            
            Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            System: AI Room Guard Agent
            
            This is an automated alert from your room security system.
            """
            msg.attach(MIMEText(body, 'plain'))
            
            # Create SMTP session
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()  # Enable security
            server.login(self.email_config['sender_email'], self.email_config['sender_password'])
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.email_config['sender_email'], self.email_config['receiver_emails'], text)
            server.quit()
            
            print("Email alert sent successfully!")
            return True
            
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
        
    def send_sms_via_email(self, phone_number, carrier, message):
        """Send SMS via email-to-SMS gateways"""
        carrier_gateways = {
            'verizon': 'vtext.com',
            'att': 'txt.att.net',
            'tmobile': 'tmomail.net',
            'sprint': 'messaging.sprintpcs.com',
            'virgin': 'vmobl.com',
            'boost': 'sms.myboostmobile.com',
            'cricket': 'sms.cricketwireless.com',
            'google': 'msg.fi.google.com'
        }
        
        if carrier not in carrier_gateways:
            print(f"Unknown carrier: {carrier}")
            return False
            
        sms_gateway = f"{phone_number}@{carrier_gateways[carrier]}"
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['sender_email']
            msg['To'] = sms_gateway
            msg['Subject'] = ""
            msg.attach(MIMEText(message))
            
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['sender_email'], self.email_config['sender_password'])
            
            text = msg.as_string()
            server.sendmail(self.email_config['sender_email'], sms_gateway, text)
            server.quit()
            
            print(f"SMS sent to {phone_number} via {carrier}")
            return True
            
        except Exception as e:
            print(f"Failed to send SMS: {e}")
            return False
    
    def send_webhook_alert(self, alert_data):
        """Send alerts to various webhook services"""
        successful_webhooks = 0
            
        # Slack-style webhook
        slack_payload = {
            "text": f"AI GUARD ALERT: {alert_data['message']}",
            "attachments": [
                {
                    "color": "danger",
                    "fields": [
                        {"title": "Time", "value": alert_data['timestamp'], "short": True},
                        {"title": "Level", "value": alert_data['level'], "short": True},
                        {"title": "Location", "value": "Your Room", "short": True}
                    ]
                }
            ]
        }
        
        # Discord-style webhook
        discord_payload = {
            "content": f"**AI GUARD ALERT**",
            "embeds": [
                {
                    "title": "Security Alert",
                    "description": alert_data['message'],
                    "color": 16711680,  # Red color
                    "fields": [
                        {"name": "Time", "value": alert_data['timestamp'], "inline": True},
                        {"name": "Escalation", "value": alert_data['level'], "inline": True}
                    ],
                    "footer": {"text": "AI Room Guard System"}
                }
            ]
        }
        
        # Try each webhook URL
        for webhook_url in self.webhook_urls:
            try:
                if 'slack.com' in webhook_url:
                    payload = slack_payload
                elif 'discord.com' in webhook_url:
                    payload = discord_payload
                else:
                    # Generic webhook
                    payload = {
                        "alert": True,
                        "message": alert_data['message'],
                        "timestamp": alert_data['timestamp'],
                        "level": alert_data['level'],
                        "system": "AI Room Guard"
                    }
                    
                response = requests.post(
                    webhook_url, 
                    json=payload, 
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                    
                if response.status_code in [200, 204]:
                    print(f"Webhook alert sent to {webhook_url}")
                    successful_webhooks += 1
                else:
                    print(f"Webhook failed with status {response.status_code}")
                        
            except Exception as e:
                print(f"Webhook error for {webhook_url}: {e}")
            
        return successful_webhooks > 0

    def send_telegram_alert(self, message, bot_token=None, chat_id=None):
        """Send alert via Telegram bot"""
        try:
            # Get from environment if not provided
            bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
            
            if not bot_token or not chat_id:
                print("Telegram bot token or chat ID not configured")
                return False
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': f"AI GUARD ALERT\n\n{message}",
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                print("Telegram alert sent!")
                return True
            else:
                print(f"Telegram API error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Telegram error: {e}")
            return False
        
    

    def ensure_face_db_directory(self):
        os.makedirs(os.path.dirname(self.face_db_path) or ".", exist_ok=True)
    def get_camera(self):
        """Thread-safe camera access with proper resource management"""
        with self.camera_lock:
            if self.camera is None or not self.camera.isOpened():
                try:
                    self.camera = cv2.VideoCapture(0)
                    if self.camera.isOpened():
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        self.camera.set(cv2.CAP_PROP_FPS, 15)
                        print("Camera opened successfully")
                        return self.camera
                    else:
                        print("Failed to open camera")
                        return None
                except Exception as e:
                    print(f"Camera error: {e}")
                    return None
            return self.camera

    def safe_camera_release(self):
        """Safely release camera with multiple attempts"""
        with self.camera_lock:
            if self.camera is not None:
                print("Releasing camera...")
                max_attempts = 3
                for attempt in range(max_attempts):
                    try:
                        self.camera.release()
                        self.camera = None
                        print("Camera released successfully")
                        break
                    except Exception as e:
                        print(f"Camera release attempt {attempt + 1} failed: {e}")
                        time.sleep(0.1)
                # Force cleanup
                cv2.destroyAllWindows()
    
    def force_camera_cleanup(self):
        """Force cleanup of all camera resources"""
        print("Force cleaning up camera resources...")
        self.safe_camera_release()
        
        # Additional cleanup
        try:
            # Close any remaining OpenCV windows
            cv2.destroyAllWindows()
            
            # Sometimes we need to wait a bit for resources to free
            time.sleep(0.5)
            
            # Try to open and immediately close a camera to reset state
            temp_cam = cv2.VideoCapture(0)
            if temp_cam.isOpened():
                temp_cam.release()
            cv2.destroyAllWindows()
            
        except Exception as e:
            print(f"Note during force cleanup: {e}")

    def load_trusted_faces(self):
        """Robust face database loading"""
        try:
            if os.path.exists(self.face_db_path):
                with open(self.face_db_path, 'rb') as f:
                    data = pickle.load(f)
                    self.known_face_encodings = data['encodings']
                    self.known_face_names = data['names']
                print(f"Loaded {len(self.known_face_names)} trusted faces")
            else:
                print("No face database found. Starting fresh.")
                self.known_face_encodings = []
                self.known_face_names = []
        except Exception as e:
            print(f"Error loading face database: {e}")
            self.known_face_encodings = []
            self.known_face_names = []

    def save_trusted_faces(self):
        """Save trusted faces to database"""
        try:
            with open(self.face_db_path, 'wb') as f:
                pickle.dump({
                    'encodings': self.known_face_encodings,
                    'names': self.known_face_names
                }, f)
            print(f"Saved {len(self.known_face_names)} faces to database")
        except Exception as e:
            print(f"Error saving face database: {e}")

    

    def _find_or_create_person_id(self,encoding):
        """Find existing person or create new ID"""
        # Check if this face matches any existing unknown person
        for person_id, data in self.unknown_person_tracker.items():
            stored_encoding = data['reference_encoding']
            distance = np.linalg.norm(stored_encoding - encoding)
            if distance < 0.6:  # Similarity threshold
                return person_id
        
        # New person - create ID
        new_id = max(self.unknown_person_tracker.keys(), default=0) + 1
        return new_id

    
    def _create_new_tracker(self, face_encoding):
        """Create new person tracker"""
        return {
            'reference_encoding': face_encoding,
            'first_seen': time.time(),
            'last_seen': time.time(),
            'escalation_level': 1,
            'response_cooldown': 30,
            'appearances': 1,
            'last_interaction': time.time()
        }

    def _update_person_tracking(self, person_id, face_encoding):
        """Update tracking and determine escalation level"""
        if person_id not in self.unknown_person_tracker:
            self.unknown_person_tracker[person_id] = self._create_new_tracker(face_encoding)
            return 1
        
        tracker = self.unknown_person_tracker[person_id]
        current_time = time.time()
        time_present = current_time - tracker['first_seen']
        
        tracker['last_seen'] = current_time
        tracker['appearances'] += 1
        
        # Determine escalation based on time present
        if time_present > 120:  # 2 minutes
            new_level = 3
        elif time_present > 60:  # 1 minute
            new_level = 2
        else:
            new_level = 1
            
        # Only escalate if level increases
        if new_level > tracker['escalation_level']:
            tracker['escalation_level'] = new_level
            tracker['response_cooldown'] = [30, 45, 60][new_level - 1]
            
        return tracker['escalation_level']
    
    def _update_situation_context(self):
        """Update dynamic context for better responses"""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            time_desc = "morning"
        elif 12 <= hour < 18:
            time_desc = "afternoon" 
        else:
            time_desc = "evening"
        
        self.situation_context['time_of_day'] = time_desc

    def _format_conversation_history(self, history):
        """Format conversation history for LLM"""
        if not history:
            return "No previous conversation"
        return "\n".join([f"{speaker}: {text}" for speaker, text in history])

    def _get_fallback_response(self, escalation_level):
        """Fallback responses when LLM fails"""
        fallbacks = {
            1: "Hello, who are you and what are you doing here?",
            2: "I need you to leave this area immediately.",
            3: "Final warning! Security is being notified. Leave now!"
        }
        return fallbacks.get(escalation_level, "Please identify yourself.")




    def setup_llm(self):
        """Configure Gemini LLM with error handling"""
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                print("GEMINI_API_KEY not found in environment")
                self.llm_model = None
                return
                
            genai.configure(api_key=api_key)
            self.llm_model = genai.GenerativeModel('gemini-pro')
            print("Gemini LLM configured successfully")
        except Exception as e:
            print(f"Error setting up LLM: {e}")
            self.llm_model = None

    def generate_escalation_response(self, escalation, context=""):
        """Generate escalation response with fallback"""
        prompts = {
            1: f"""As a room guard AI, politely inquire about an unknown person. 
            Context: {context}
            Generate a calm, polite inquiry asking who they are and what they're doing here.""",
            
            2: f"""As a room guard AI, issue a firm warning to an unknown person who hasn't identified themselves.
            Context: {context}
            Generate a firm but professional warning asking them to leave immediately.""",
            
            3: f"""As a room guard AI, issue a final alert for an intruder who hasn't left after warnings.
            Context: {context}
            Generate a stern alert stating that authorities are being notified and they must leave immediately."""
        }
        
        prompt = prompts.get(escalation, prompts[1])
        
        try:
            if self.llm_model:
                response = self.llm_model.generate_content(prompt)
                return response.text.strip()
            else:
                # Fallback responses
                fallbacks = {
                    1: "Hello, who are you and what are you doing here?",
                    2: "I need you to leave this area immediately.",
                    3: "Final warning! Security is being notified. Leave now!"
                }
                return fallbacks.get(escalation, "Please identify yourself.")
                
        except Exception as e:
            print(f"LLM error: {e}")
            return "Please identify yourself and state your purpose."
    def activate_alarm_protocol(self):
        """Real alarm functionality for level 3 escalation"""
        if self.alarm_activated:
            return
            
        self.alarm_activated = True
        
        # Visual alarm
        alarm_thread = threading.Thread(target=self._flash_alarm, daemon=True)
        alarm_thread.start()
        
        # Audio alarm
        self.speak("INTRUDER ALERT! Security has been notified! Leave immediately!")
        
        # Notify authorities
        self.notify_authorities()
        
        print("ALARM ACTIVATED - Authorities notified")

    def _flash_alarm(self):
        """Visual alarm display"""
        while self.alarm_activated and self.guard_mode:
            # Create flashing alert window
            for color in [(0, 0, 255), (0, 0, 0)]:  # Red, Black
                alert_frame = np.zeros((200, 600, 3), dtype=np.uint8)
                alert_frame[:] = color
                
                cv2.putText(alert_frame, "INTRUDER ALERT!", (50, 100),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)
                cv2.imshow("ALERT - INTRUDER DETECTED", alert_frame)
                cv2.waitKey(500)  # Flash every 500ms
                
        cv2.destroyWindow("ALERT - INTRUDER DETECTED")

    def notify_authorities(self, escalation_level, context=""):
        """Complete authority notification system"""
        alert_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': f"Level {escalation_level}",
            'message': self._get_alert_message(escalation_level, context)
        }
        
        print(f"NOTIFYING AUTHORITIES: {alert_data['message']}")
        
        success_count = 0
        
        # Level 1-2: Basic notifications
        if escalation_level >= 1:
            # Log to file (always works)
            self._log_alert_to_file(alert_data)
            success_count += 1
            
            # Email alert for level 2+
            if escalation_level >= 2:
                email_subject = f"AI Guard Alert - Level {escalation_level}"
                if self.send_alert_email(email_subject, alert_data['message']):
                    success_count += 1
        
        # Level 3: Full emergency notifications
        if escalation_level >= 3:
            # Webhook alerts
            if self.send_webhook_alert(alert_data):
                success_count += 1
            
            # SMS via email
            if self.send_sms_via_email('5551234567', 'verizon', alert_data['message']):  # Configure your number
                success_count += 1
            
            # Telegram
            if self.send_telegram_alert(alert_data['message']):
                success_count += 1
            
            # Additional emergency contacts
            emergency_contacts = os.getenv('EMERGENCY_CONTACTS', '').split(',')
            for contact in emergency_contacts:
                if contact.strip():
                    # Could be phone numbers for SMS or emails
                    if '@' in contact:
                        # It's an email
                        self.send_alert_email(f"URGENT: {alert_data['message']}", contact)
                    else:
                        # Assume it's a phone number for SMS
                        self.send_sms_via_email(contact.strip(), 'verizon', alert_data['message'])
        
        print(f"{success_count} notification methods successful")
        return success_count > 0

    def _get_alert_message(self, escalation_level, context):
        """Generate appropriate alert message"""
        messages = {
            1: f"Unknown person detected. {context}",
            2: f"UNKNOWN PERSON WARNING: Person has not left after initial warning. {context}",
            3: f"INTRUDER ALERT: Unknown person remains after multiple warnings! {context}"
        }
        return messages.get(escalation_level, f"Security alert: {context}")

    def _log_alert_to_file(self, alert_data):
        """Always log alerts to local file"""
        try:
            with open("security_alerts.log", "a", encoding='utf-8') as f:
                f.write(f"{alert_data['timestamp']} - {alert_data['level']}: {alert_data['message']}\n")
            print("Alert logged to security_alerts.log")
        except Exception as e:
            print(f"Failed to log alert: {e}")

    def handle_unknown_person(self, face_encoding, frame):
        """Enhanced with real notifications"""
        person_id = self._find_or_create_person_id(face_encoding[0] if isinstance(face_encoding, list) else face_encoding)
        
        escalation_level = self._update_person_tracking(person_id, face_encoding)
        current_time = time.time()
        tracker = self.unknown_person_tracker[person_id]
        
        if current_time - tracker['last_interaction'] > tracker['response_cooldown']:
            context = f"Present for {int(current_time - tracker['first_seen'])}s, seen {tracker['appearances']} times"
            
            # Generate and speak response
            response = self.generate_escalation_response(escalation_level, person_id, context)
            self.speak(response)
            print(f"Level {escalation_level}: {response}")
            
            # SEND ACTUAL NOTIFICATIONS
            if escalation_level >= 2:  # Level 2+ triggers external notifications
                self.notify_authorities(escalation_level, context)
            
            # Level 3: Additional emergency measures
            if escalation_level == 3:
                self.activate_alarm_protocol()
                # Take photo evidence
                self._capture_evidence_frame(frame, person_id)
            
            tracker['last_interaction'] = current_time

    def _capture_evidence_frame(self, frame, person_id):
        """Save photo evidence of intruder"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evidence_person_{person_id}_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            print(f" Evidence saved: {filename}")
        except Exception as e:
            print(f"Failed to save evidence: {e}")
    def _find_matching_person(self,encoding,threshold=0.1):
        for person_id, data in self.unknown_person_tracker.items():
            stored_encoding = data['reference_encoding']
            distance = np.linalg.norm(stored_encoding - encoding)
            if distance < threshold:
                return person_id
        return None 
 
    


    def speak(self, text):
        """Text to speech with error handling"""
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            print(f"TTS error: {e}")
    
    
    
    def enroll_using_webcam(self, name="unknown"):
        """Face enrollment with proper camera cleanup"""
        camera = self.get_camera()
        if not camera or not camera.isOpened():
            self.speak("Cannot access camera for enrollment.")
            return False

        self.speak(f"Please look at the camera for face enrollment as {name}")

        enrollment_frames = []
        frames_captured = 0
        max_frames = 10  # Reduced for faster enrollment
        
        try:
            while frames_captured < max_frames and not self.stop_flag:
                ret, frame = camera.read()
                if not ret:
                    print(" Failed to capture frame")
                    continue
                
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_frame)
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                
                if len(face_encodings) == 1:
                    enrollment_frames.append(face_encodings[0])
                    frames_captured += 1
                    print(f" Captured face frame {frames_captured}/{max_frames}")
                    
                    cv2.putText(frame, f"Enrolling: {frames_captured}/{max_frames}", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow("Face Enrollment - Press 'q' to cancel", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                time.sleep(0.3)
            
            if enrollment_frames:
                avg_encoding = np.mean(enrollment_frames, axis=0)
                self.known_face_encodings.append(avg_encoding)
                self.known_face_names.append(name)
                self.save_trusted_faces()
                self.speak(f"Successfully enrolled {name} as a trusted person")
                return True
            else:
                self.speak("Failed to capture face. Please try again.")
                return False
                
        except Exception as e:
            print(f"Enrollment error: {e}")
            self.speak("Error during face enrollment.")
            return False
        finally:
            # ALWAYS cleanup
            cv2.destroyAllWindows()
            print("Enrollment camera cleanup completed")
        
    # === FIXED MIC STREAM ===
    def mic_stream(self):
        """Capture microphone audio in chunks"""
        def callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")
            if not self.audio_queue.full():  # Prevent queue overload
                self.audio_queue.put(indata.copy())
        
        try:
            with sd.InputStream(
                samplerate=self.SAMPLE_RATE, 
                channels=1, 
                dtype='int16', 
                callback=callback,
                blocksize=int(self.SAMPLE_RATE * self.CHUNK_SECONDS)
            ):
                print(" Microphone stream started")
                while not self.stop_flag:
                    time.sleep(0.1)
        except Exception as e:
            print(f"Microphone error: {e}")
        finally:
            print(" Microphone stream stopped")


    def check_activation_command(self, text):
        """Check if text contains any activation phrase"""
        return any(phrase in text for phrase in self.activation_phrases)
    
    def check_deactivation_command(self, text):
        """Check if text contains any deactivation phrase"""
        return any(phrase in text for phrase in self.deactivation_phrases)
    
    def check_enrollment_command(self, text):
        """Check if text contains face enrollment phrase"""
        return any(phrase in text for phrase in self.enrollment_phrases)
    
    def activate_guard_mode(self):
        """Activate guard mode with proper resource management"""
        self.guard_mode = True
        self.unknown_person_tracker = {}
        self.conversation_memory = {}
        self.alarm_activated = False
        
        self.speak("Guard mode activated! Starting face monitoring.")
        print(f"Guard mode ACTIVATED at {datetime.now().strftime('%H:%M:%S')}")
        
        # Start face monitoring in a separate thread
        face_thread = threading.Thread(target=self.face_monitoring_loop, daemon=True)
        face_thread.start()

    
    def deactivate_guard_mode(self):
        """Deactivate guard mode with proper cleanup"""
        print("Deactivating guard mode and cleaning up...")
        self.guard_mode = False
        self.alarm_activated = False
        
        # Allow time for monitoring loop to exit
        time.sleep(0.5)
        
        # Force cleanup
        self.force_camera_cleanup()
        
        self.speak("Guard mode deactivated. Goodbye!")
        print(f"Guard mode DEACTIVATED at {datetime.now().strftime('%H:%M:%S')}")


    def process_audio_chunk(self, chunk):
        """Process audio chunk with Whisper"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            path = tmp.name
        
        try:
            wv(path, self.SAMPLE_RATE, chunk)
            result = self.model.transcribe(
                path, 
                language="en", 
                fp16=False, 
                condition_on_previous_text=False
            )
            
            text = (result.get("text") or "").strip().lower()
            
            if text:
                print(f"Heard: {text}")
                
                if self.check_activation_command(text) and not self.guard_mode:
                    self.activate_guard_mode()
                elif self.check_deactivation_command(text) and self.guard_mode:
                    self.deactivate_guard_mode()
                elif self.check_enrollment_command(text):
                    self.speak("Starting face enrollment process.")
                    self.enroll_using_webcam()
                elif "how many trusted" in text or "list trusted" in text:
                    count = len(self.known_face_names)
                    if count == 0:
                        self.speak("No trusted faces enrolled yet.")
                    else:
                        self.speak(f"I have {count} trusted faces enrolled.")
                        print(f"Trusted faces: {', '.join(self.known_face_names)}")
                elif self.guard_mode:
                    print(f" In guard mode, heard: {text}")
                    
        except Exception as e:
            print(f"Error processing audio: {e}")
        finally:
            if os.path.exists(path):
                os.remove(path)
    
    def recognize(self, frame):
        """Recognize faces in frame"""
        if not self.known_face_encodings:
            return [], [], []
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(frame_rgb)
        face_encodings = face_recognition.face_encodings(frame_rgb, face_locations)
        
        recognized_names = []
        recognized_status = []
        
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.5)
            name = "unknown"
            status = "unknown"
            
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances) if len(face_distances) > 0 else None
            
            if best_match_index is not None and matches[best_match_index]:
                name = self.known_face_names[best_match_index]
                status = "trusted"
            
            recognized_names.append(name)
            recognized_status.append(status)
        
        return recognized_names, recognized_status, face_encodings
    
    def face_monitoring_loop(self):
        """Face monitoring with guaranteed cleanup"""
        print("Starting face monitoring loop...")
        camera = self.get_camera()
        
        if not camera or not camera.isOpened():
            self.speak("Error accessing the webcam for face monitoring.")
            print("Error: Could not open webcam.")
            self.guard_mode = False
            return
        
        self.speak("Face monitoring started. Scanning for trusted individuals.")
        last_announcement = {}
        announcement_cd = 30

        try:
            while self.guard_mode and not self.stop_flag:
                ret, frame = camera.read()
                if not ret:
                    print("Failed to capture frame from webcam")
                    time.sleep(1)
                    continue
                
                names, statuses, encodings = self.recognize(frame)
                curr_t = time.time()
                
                for name, status, encoding in zip(names, statuses, encodings):
                    if status == "trusted":
                        if name not in last_announcement or (curr_t - last_announcement[name]) > announcement_cd:
                            self.speak(f"Hello {name}, welcome back!")
                            print(f" Recognized trusted person: {name}")
                            last_announcement[name] = curr_t
                    elif status == "unknown":
                        if "unknown" not in last_announcement or (curr_t - last_announcement["unknown"]) > 10:
                            self.speak("Alert! Unknown person detected!")
                            self.handle_unknown_person(encoding, frame)
                            print(" Alert! Unknown person detected!")
                            last_announcement["unknown"] = curr_t
                
                # Draw face boxes
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(frame_rgb)
                
                for (top, right, bottom, left), name, status in zip(face_locations, names, statuses):
                    color = (0, 255, 0) if status == "trusted" else (0, 0, 255)
                    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                    cv2.putText(frame, f"{name} ({status})", (left, top - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                cv2.imshow("AI Guard - Face Monitoring (Press 'q' to stop)", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except Exception as e:
            print(f"Face monitoring error: {e}")
        finally:
            # GUARANTEED CLEANUP - This always runs
            print("Cleaning up face monitoring resources...")
            cv2.destroyAllWindows()
            self.safe_camera_release()
            print("Face monitoring cleanup completed")

    

  
    def start_listening(self):
        """Start the system with proper initialization"""
        self.listening = True
        self.stop_flag = False
        
        # Start microphone stream
        audio_thread = threading.Thread(target=self.mic_stream, daemon=True)
        audio_thread.start()
        
        self.speak("AI Guard system ready. Say 'Guard my room' to activate or 'Enroll face' to add trusted persons.")
        print(" Listening for commands...")
        print(f" {len(self.known_face_names)} trusted faces loaded")
        
        try:
            while self.listening and not self.stop_flag:
                if not self.audio_queue.empty():
                    chunk = self.audio_queue.get()
                    self.process_audio_chunk(chunk)
                else:
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            print("\n Keyboard interrupt received...")
        except Exception as e:
            print(f"\n Unexpected error: {e}")
        finally:
            # GUARANTEED CLEANUP
            self.stop_listening()
    
    def stop_listening(self):
        """Complete system shutdown with guaranteed cleanup"""
        print("\n Shutting down AI Guard system...")
        
        # Set flags to stop all loops
        self.listening = False
        self.stop_flag = True
        self.guard_mode = False
        self.alarm_activated = False
        
        # Allow time for threads to exit
        time.sleep(1)
        
        # Force cleanup of all resources
        self.force_camera_cleanup()
        
        # Clear queues
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except:
                break
                
        print(" AI Guard system shutdown complete")
        print(" Camera should now be released and available for other applications")
    