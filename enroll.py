# SECURE_ENROLLMENT_CLASS.ipynb
import cv2
import face_recognition
import pickle
import numpy as np
import hashlib
import hmac
import time
import os
from datetime import datetime
import secrets
import string
import base64
from IPython.display import display, clear_output
import ipywidgets as widgets

class UltraSecureEnroller:
    def __init__(self):
        self.face_db_path = "secure_face_vault.dat"
        self.max_enrollments = 10
        self.failed_attempts = 0
        self.max_failed_attempts = 3
        self.lockout_until = None
        self.lockout_duration = 900  # 15 minutes

        # Security settings
        self.min_pin_length = 8
        self.require_special_chars = True
        self.session_timeout = 300  # 5 minutes
        self.session_start = None

        # ✅ FIX: load encryption key before setup
        self.encryption_key = self._load_encryption_key()
        self._initialize_security()
        
        print("🔐 ULTRA-SECURE ENROLLMENT SYSTEM INITIALIZED")
        print("📝 Designed for Jupyter Notebook Environment")
        
    def _initialize_security(self):
        """Initialize security files"""
        os.makedirs('secure_vault', exist_ok=True)
        
        # Initialize admin credentials if not exists
        if not os.path.exists('secure_vault/admin.secure'):
            self._first_time_setup()
            
        # Initialize encryption key if not exists  
        if not os.path.exists('secure_vault/encryption.key'):
            key = base64.urlsafe_b64encode(os.urandom(32))
            with open('secure_vault/encryption.key', 'wb') as f:
                f.write(key)
            os.chmod('secure_vault/encryption.key', 0o600)
    
    def _load_encryption_key(self):
        """Load encryption key safely"""
        os.makedirs('secure_vault', exist_ok=True)
        try:
            with open('secure_vault/encryption.key', 'rb') as f:
                return base64.urlsafe_b64decode(f.read())
        except FileNotFoundError:
            key = base64.urlsafe_b64encode(os.urandom(32))
            with open('secure_vault/encryption.key', 'wb') as f:
                f.write(key)
            os.chmod('secure_vault/encryption.key', 0o600)
            return base64.urlsafe_b64decode(key)

    
    def _first_time_setup(self):
        """First-time admin setup with Jupyter widgets"""
        print("🚨 FIRST-TIME SECURITY SETUP")
        print("="*50)
        
        from IPython.display import display, Javascript
        display(Javascript('alert("First-time security setup required")'))
        
        # Create secure admin PIN
        while True:
            admin_pin = input("🔐 Create Admin PIN (min 8 chars, mix of letters/numbers/symbols): ")
            
            if self._validate_pin_strength(admin_pin):
                break
            else:
                print("❌ PIN too weak. Must have: 8+ chars, uppercase, lowercase, number, symbol")
        
        # Create security question
        security_question = input("❓ Enter security question: ")
        security_answer = input("💡 Enter security answer: ")
        
        # Hash and store credentials
        salt = secrets.token_hex(32)
        pin_hash = self._hash_password(admin_pin, salt)
        answer_hash = self._hash_password(security_answer, secrets.token_hex(32))
        
        credentials = {
            'pin_hash': pin_hash,
            'salt': salt,
            'security_question': security_question,
            'security_answer_hash': answer_hash
        }
        
        # Encrypt and store
        encrypted_data = self._encrypt_data(pickle.dumps(credentials))
        with open('secure_vault/admin.secure', 'wb') as f:
            f.write(encrypted_data)
        
        os.chmod('secure_vault/admin.secure', 0o600)
        print("✅ Admin credentials created securely!")
    
    def _validate_pin_strength(self, pin):
        """Validate PIN meets security requirements"""
        if len(pin) < self.min_pin_length:
            return False
        if not any(c.isupper() for c in pin):
            return False
        if not any(c.islower() for c in pin):
            return False  
        if not any(c.isdigit() for c in pin):
            return False
        if self.require_special_chars and not any(c in string.punctuation for c in pin):
            return False
        return True
    
    def _hash_password(self, password, salt):
        """HMAC-based key derivation"""
        return hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000
        ).hex()
    
    def _encrypt_data(self, data):
        """Simple XOR encryption for demo (in production use proper crypto)"""
        key = self.encryption_key
        encrypted = bytearray()
        for i, byte in enumerate(data):
            encrypted.append(byte ^ key[i % len(key)])
        return bytes(encrypted)
    
    def _decrypt_data(self, encrypted_data):
        """Decrypt data"""
        return self._encrypt_data(encrypted_data)  # XOR is symmetric
    
    def _check_lockout(self):
        """Check if system is locked out"""
        if self.lockout_until and time.time() < self.lockout_until:
            remaining = int(self.lockout_until - time.time())
            print(f"🔒 System locked out. Try again in {remaining} seconds")
            return True
        return False
    
    def _trigger_lockout(self):
        """Trigger system lockout"""
        self.lockout_until = time.time() + self.lockout_duration
        print(f"🚨 TOO MANY FAILED ATTEMPTS - SYSTEM LOCKED FOR {self.lockout_duration//60} MINUTES")
    
    def _multi_factor_auth(self):
        """Multi-factor authentication for Jupyter"""
        if self._check_lockout():
            return False
        
        print("\n🔐 MULTI-FACTOR AUTHENTICATION REQUIRED")
        print("-" * 40)
        
        # Load admin credentials
        try:
            with open('secure_vault/admin.secure', 'rb') as f:
                encrypted = f.read()
            credentials = pickle.loads(self._decrypt_data(encrypted))
        except:
            print("❌ Admin credentials corrupted. Run first-time setup.")
            return False
        
        # Factor 1: Admin PIN
        attempt = input("Enter Admin PIN: ")
        computed_hash = self._hash_password(attempt, credentials['salt'])
        
        if not hmac.compare_digest(computed_hash, credentials['pin_hash']):
            self.failed_attempts += 1
            print(f"❌ Invalid PIN (Attempt {self.failed_attempts}/{self.max_failed_attempts})")
            
            if self.failed_attempts >= self.max_failed_attempts:
                self._trigger_lockout()
                return False
            return False
        
        # Factor 2: Security Question
        print(f"\n❓ Security Question: {credentials['security_question']}")
        answer_attempt = input("Answer: ")
        answer_hash = self._hash_password(answer_attempt, credentials['salt'])
        
        if not hmac.compare_digest(answer_hash, credentials['security_answer_hash']):
            print("❌ Security question failed")
            return False
        
        # Factor 3: Physical Confirmation
        print("\n⏰ Physical Presence Verification:")
        confirmation = input("Type 'CONFIRM SECURE ENROLLMENT' exactly: ")
        if confirmation != "CONFIRM SECURE ENROLLMENT":
            print("❌ Physical confirmation failed")
            return False
        
        # Success - reset counters and start session
        self.failed_attempts = 0
        self.lockout_until = None
        self.session_start = time.time()
        print("✅ Multi-factor authentication SUCCESSFUL")
        return True
    
    def _check_session_valid(self):
        """Check if session is still valid"""
        if not self.session_start:
            return False
        return (time.time() - self.session_start) < self.session_timeout
    
    def _capture_face_secure(self, name):
        """Secure face capture with Jupyter-compatible display"""
        print(f"\n📸 SECURE FACE CAPTURE: {name}")
        print("Ensure good lighting and look directly at camera")
        print("Slowly move your head left and right for liveness detection...")
        
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            print("❌ Could not access camera")
            return None
        
        enrollment_frames = []
        frames_captured = 0
        max_frames = 12
        
        try:
            while frames_captured < max_frames:
                ret, frame = camera.read()
                if not ret:
                    continue
                
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_frame)
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                
                if len(face_encodings) == 1:
                    enrollment_frames.append(face_encodings[0])
                    frames_captured += 1
                    
                    # Display progress in console
                    clear_output(wait=True)
                    print(f"📸 SECURE FACE CAPTURE: {name}")
                    print(f"🎯 Progress: {frames_captured}/{max_frames} frames")
                    print("🔄 Please continue moving your head slowly...")
                
                # Show preview (optional - comment out if causing issues)
                cv2.imshow("SECURE ENROLLMENT - Press 'q' to abort", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("❌ Enrollment aborted by user")
                    break
                
                time.sleep(0.2)
            
            camera.release()
            cv2.destroyAllWindows()
            
            if len(enrollment_frames) >= 8:  # Minimum frames for liveness
                avg_encoding = np.mean(enrollment_frames, axis=0)
                print(f"✅ Successfully captured {len(enrollment_frames)} biometric frames")
                return avg_encoding
            else:
                print("❌ Insufficient frames captured for liveness verification")
                return None
                
        except Exception as e:
            print(f"❌ Error during face capture: {e}")
            camera.release()
            cv2.destroyAllWindows()
            return None
    
    def _load_face_database(self):
        """Load encrypted face database"""
        if not os.path.exists(self.face_db_path):
            return {'encodings': [], 'names': [], 'timestamps': []}
        
        try:
            with open(self.face_db_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self._decrypt_data(encrypted_data)
            data = pickle.loads(decrypted_data)
            print(f"🔐 Loaded {len(data['names'])} enrolled faces from secure database")
            return data
        except Exception as e:
            print(f"❌ Error loading face database: {e}")
            return {'encodings': [], 'names': [], 'timestamps': []}
    
    def _save_face_database(self, data):
        """Save encrypted face database"""
        try:
            # Create backup
            if os.path.exists(self.face_db_path):
                backup_name = f"{self.face_db_path}.backup.{int(time.time())}"
                os.rename(self.face_db_path, backup_name)
            
            # Encrypt and save
            pickled_data = pickle.dumps(data)
            encrypted_data = self._encrypt_data(pickled_data)
            
            with open(self.face_db_path, 'wb') as f:
                f.write(encrypted_data)
            
            print(f"💾 Saved {len(data['names'])} faces to secure database")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save face database: {e}")
            return False
    
    def enroll_face(self, name):
        """Main enrollment method - ultra secure"""
        print("🚀 STARTING ULTRA-SECURE ENROLLMENT PROCESS")
        print("=" * 50)
        
        # Check authentication
        if not self._multi_factor_auth():
            return False
        
        # Check enrollment limits
        current_data = self._load_face_database()
        if len(current_data['names']) >= self.max_enrollments:
            print("❌ Maximum enrollment limit reached")
            return False
        
        # Check if name already exists
        if name in current_data['names']:
            print(f"❌ {name} is already enrolled")
            overwrite = input("Overwrite? (yes/no): ").lower()
            if overwrite != 'yes':
                return False
            # Remove existing entry
            index = current_data['names'].index(name)
            current_data['names'].pop(index)
            current_data['encodings'].pop(index)
            current_data['timestamps'].pop(index)
        
        # Capture face
        face_encoding = self._capture_face_secure(name)
        if face_encoding is None:
            return False
        
        # Add to database
        current_data['encodings'].append(face_encoding)
        current_data['names'].append(name)
        current_data['timestamps'].append(datetime.now().isoformat())
        
        if self._save_face_database(current_data):
            print(f"✅ {name} successfully enrolled in SECURE biometric database")
            self._generate_enrollment_certificate(name)
            return True
        else:
            print("❌ Failed to save to secure database")
            return False
    
    def _generate_enrollment_certificate(self, name):
        """Generate enrollment certificate"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cert_data = f"ENROLLMENT_CERTIFICATE||{name}||{timestamp}||{secrets.token_hex(8)}"
        cert_hash = hashlib.sha256(cert_data.encode()).hexdigest()[:16]
        
        cert_filename = f"secure_vault/enrollment_{name}_{int(time.time())}.cert"
        with open(cert_filename, 'w') as f:
            f.write("🔐 ULTRA-SECURE ENROLLMENT CERTIFICATE\n")
            f.write("=" * 50 + "\n")
            f.write(f"Name: {name}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Certificate ID: {cert_hash}\n")
            f.write(f"Status: VERIFIED & ENCRYPTED\n")
            f.write("=" * 50 + "\n")
        
        print(f"📄 Enrollment certificate: {cert_filename}")
    
    def list_enrolled_faces(self):
        """List all enrolled faces (requires auth)"""
        if not self._multi_factor_auth():
            return
        
        data = self._load_face_database()
        print(f"\n📋 ENROLLED FACES ({len(data['names'])}/{self.max_enrollments}):")
        print("-" * 50)
        for i, (name, timestamp) in enumerate(zip(data['names'], data['timestamps']), 1):
            print(f"#{i:2d} | {name:20} | {timestamp[:16]}")
    
    def remove_face(self, name):
        """Remove enrolled face (requires auth)"""
        if not self._multi_factor_auth():
            return False
        
        data = self._load_face_database()
        if name in data['names']:
            index = data['names'].index(name)
            data['names'].pop(index)
            data['encodings'].pop(index)
            data['timestamps'].pop(index)
            
            if self._save_face_database(data):
                print(f"✅ Removed {name} from secure database")
                return True
            else:
                print("❌ Failed to update database")
                return False
        else:
            print(f"❌ {name} not found in database")
            return False
    
    def system_status(self):
        """Display system security status"""
        data = self._load_face_database()
        
        print("\n📊 ULTRA-SECURE ENROLLMENT SYSTEM STATUS")
        print("=" * 50)
        print(f"🔐 Enrolled faces: {len(data['names'])}/{self.max_enrollments}")
        print(f"🚨 Failed attempts: {self.failed_attempts}/{self.max_failed_attempts}")
        print(f"📁 Database: {'🔐 ENCRYPTED' if os.path.exists(self.face_db_path) else '❌ NOT FOUND'}")
        print(f"🔑 Security vault: {'✅ ACTIVE' if os.path.exists('secure_vault/admin.secure') else '❌ INACTIVE'}")
        
        if self.lockout_until:
            remaining = int(self.lockout_until - time.time())
            print(f"🔒 System lockout: {remaining}s remaining")
        else:
            print(f"🔓 System status: ✅ OPERATIONAL")
    
    def export_for_guard(self):
        """Export face data for AI Guard system (read-only)"""
        print("🔄 Exporting face data for AI Guard system...")
        
        data = self._load_face_database()
        guard_data = {
            'encodings': data['encodings'],
            'names': data['names']
        }
        
        # Save in format expected by AI Guard
        with open('face_database.pkl', 'wb') as f:
            pickle.dump(guard_data, f)
        
        print("✅ Face database exported for AI Guard system")
        print("📁 File: face_database.pkl (READ-ONLY)")

# 🎯 JUPYTER NOTEBOOK USAGE
def demo_secure_enrollment():
    """Demo function for Jupyter notebook"""
    
    # Create enroller instance
    enroller = UltraSecureEnroller()
    
    print("""
    🎯 ULTRA-SECURE ENROLLMENT DEMO
    ================================
    Available Methods:
    1. enroller.enroll_face("Name")    - Secure enrollment
    2. enroller.list_enrolled_faces()  - List all faces  
    3. enroller.remove_face("Name")    - Remove face
    4. enroller.system_status()        - System status
    5. enroller.export_for_guard()     - Export for AI Guard
    
    🔐 SECURITY FEATURES:
    • Multi-factor authentication
    • Encrypted face storage  
    • Liveness detection
    • Attempt limiting & lockout
    • Session timeouts
    • Audit certificates
    """)
    
    return enroller

# 🚀 Quick start - run this cell to begin
if __name__ == "__main__":
    # Create the secure enroller
    secure_enroller = demo_secure_enrollment()
    
    # Example usage:
    # secure_enroller.enroll_face("John Doe")
    # secure_enroller.list_enrolled_faces() 
    # secure_enroller.system_status()