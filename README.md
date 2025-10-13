# AI Guard Agent - EE782 Course Assignment

![AI Guard System](https://img.shields.io/badge/AI-Security%20System-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

##  Overview

The **AI Guard Agent** is an intelligent room security system that combines voice recognition, facial recognition, and real-time monitoring to provide automated security protection. This project was developed as part of the EE782 course assignment, demonstrating practical applications of artificial intelligence in security systems.

##  Key Features

###  Voice Command System
- **Voice Activation**: Activate guard mode with natural language commands
- **Real-time Speech Recognition**: Uses Whisper AI for accurate speech-to-text
- **Multiple Command Support**:
  - "Guard my room", "Protect my room", "Start guard mode"
  - "Stop guard mode", "Deactivate guard"
  - "Enroll face", "Register face"

###  Facial Recognition & Management
- **Trusted Face Database**: Secure storage of authorized individuals
- **Real-time Face Detection**: Continuous monitoring with OpenCV
- **Automatic Enrollment**: Easy addition of new trusted faces via webcam
- **Unknown Person Tracking**: Escalation system for unauthorized individuals

###  Intelligent Escalation System
- **Level 1**: Polite inquiry and identification request
- **Level 2**: Firm warning with authority notifications
- **Level 3**: Intruder alert with alarm activation and evidence capture

###  Multi-Channel Alert System
- **Slack Integration**: Real-time webhook notifications
- **Local Logging**: Comprehensive security event logging
- **Visual Alarms**: Flashing alert displays
- **Audio Alarms**: Text-to-speech warnings

###  Technical Capabilities
- **Real-time Audio Processing**: Continuous microphone monitoring
- **Camera Management**: Thread-safe webcam access
- **Resource Optimization**: Efficient memory and CPU usage
- **Error Handling**: Robust exception management

##  Installation & Setup

### Prerequisites
- Python 3.10+
- Webcam and microphone
- Internet connection for AI services

### Required Libraries
```bash
pip install whisper opencv-python face-recognition pyttsx3 sounddevice google-genai python-dotenv requests
```

### Environment Configuration
Create a `.env` file with:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GUARD_WEBHOOKS=your_slack_webhook_url_here
```

##  Usage

### Starting the System
```python
from ai_guard_agent import AIGuardAgent

guard = AIGuardAgent()
guard.start_listening()
```

### Voice Commands
1. **Activate Security**: "Guard my room" or "Protect my room"
2. **Add Trusted Person**: "Enroll face" or "Register face"
3. **Deactivate**: "Stop guard mode" or "Stand down"
4. **Check Status**: "How many trusted faces?"

### Manual Operations
- **Face Enrollment**: System guides through webcam capture process
- **Monitoring**: Automatic face detection and recognition
- **Escalation**: Progressive responses based on threat level

## 🏗️ System Architecture

### Core Components
1. **Audio Processing Module**
   - Real-time microphone streaming
   - Whisper AI transcription
   - Voice command interpretation

2. **Visual Monitoring Module**
   - OpenCV-based face detection
   - Face recognition and tracking
   - Real-time video processing

3. **AI Decision Engine**
   - Gemini AI for contextual responses
   - Escalation logic
   - Conversation memory

4. **Notification System**
   - Multi-platform alerts
   - Evidence capture
   - Security logging

### Data Flow
```
Audio Input → Speech Recognition → Command Processing
     ↓
Camera Feed → Face Detection → Recognition → Escalation Logic
     ↓
AI Response Generation → Audio Output + Notifications
```

##  Security Features

### Access Control
- **Biometric Authentication**: Face-based access control
- **Voice Activation**: Secure voice command system
- **Progressive Security**: Multi-level response system

### Privacy Protection
- **Local Processing**: Face data stored locally
- **Optional Cloud**: AI services can be configured
- **Data Encryption**: Secure storage of biometric data

### Alert System
- **Immediate Notifications**: Real-time alert delivery
- **Evidence Collection**: Automatic photo capture
- **Audit Trail**: Comprehensive activity logging

##  File Structure
```
ai_guard_agent/
├── ai_guard_agent.py    # Main system class
├── face_database.pkl    # Trusted faces storage
├── security_alerts.log  # Security event log
├── evidence_*.jpg       # Captured evidence images
└── requirements.txt     # Dependencies
```

## Configuration Options

### System Parameters
- **Sample Rate**: 16000 Hz (audio)
- **Chunk Size**: 2 seconds (audio processing)
- **Face Recognition Tolerance**: 0.5
- **Escalation Timers**: 60s (Level 2), 120s (Level 3)

### Customization
- Modify activation phrases in `activation_phrases`
- Adjust escalation thresholds in `escalation_levels`
- Configure notification channels in `_load_notification_config`

##  Troubleshooting

### Common Issues
1. **Camera Access**: Ensure no other application is using the webcam
2. **Microphone Permissions**: Grant audio access to Python
3. **API Keys**: Verify Gemini API key in environment variables
4. **Dependencies**: Install all required libraries

### Performance Tips
- Use adequate lighting for better face recognition
- Ensure clear audio input for voice commands
- Close unnecessary applications during operation

## Future Enhancements

### Planned Features
- **Mobile App Integration**: Remote monitoring and control
- **Multiple Camera Support**: Expanded coverage areas
- **Advanced Analytics**: Behavior pattern recognition
- **IoT Integration**: Smart home device coordination

### Technical Improvements
- **Edge AI**: On-device model processing
- **Cloud Backup**: Secure remote storage
- **Multi-language Support**: Expanded voice command languages

##  Development Team
This project was developed as part of **EE782 ** course assignment, demonstrating practical implementation of AI technologies in security systems.

##  License
This project is licensed under the MIT License - see the LICENSE file for details.

##  Disclaimer
This system is designed for educational purposes as part of academic coursework. Users are responsible for complying with local laws and regulations regarding surveillance and privacy.

---
Course:EE782
