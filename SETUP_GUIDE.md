# AI-Assistant - Deployment & Setup Guide

## Option 1: Standalone EXE (Recommended for Distribution)

### System Requirements
- Windows 10 or later (64-bit)
- No Python installation required
- Internet connection for API calls
- Microphone or audio input device

### Setup Instructions

1. **Download the EXE**
   - File: `dist/AI-Assistant.exe`
   - Size: ~122 MB

2. **First Run Setup**
   - Double-click `AI-Assistant.exe`
   - The app will open with Settings panel on the right
   - Go to **🔑 API Keys** tab

3. **Configure API Keys**
   - **Azure Speech API Key**: Get from https://portal.azure.com
     - Create a Cognitive Services > Speech resource
     - Copy the API Key
   - **Azure Region**: e.g., `eastus`, `westus2` (from your Azure resource)
   - **Gemini API Key**: Get from https://aistudio.google.com/app/apikey
     - Create a new API key (free tier available)
   - Click **💾 Save API Keys**

4. **Start Using**
   - Click **🎤 Start Transcription** to record audio
   - Press **Alt+X** to capture and analyze screenshots
   - The app stays on top and is transparent (opacity: 53%)

### Troubleshooting

**"Error: Install pyaudiowpatch for system audio"**
- The app will automatically fall back to microphone input
- If you want system audio loopback:
  1. Install Python 3.11+
  2. Install PyAudioWPatch: `pip install pyaudiowpatch`
  3. Run from Python instead

**"Unhandled exception: Azure DLL not found"**
- Try the **Python launcher** option below instead
- Report the issue with full error message

---

## Option 2: Python Launcher (Alternative - Easier Setup)

If the EXE has issues, use the batch file launcher instead.

### Requirements
- Python 3.11+ (from https://python.org)
- Windows 10 or later

### Setup Instructions

1. **Install Python**
   - Download from https://python.org
   - ✅ Check "Add Python to PATH" during installation
   - Verify: Open PowerShell, run `python --version`

2. **Install Dependencies**
   - Open PowerShell in the project folder
   - Run: `pip install -r requirements.txt`
   - Wait for all packages to install

3. **Run the App**
   - Double-click `RUN_ME.bat` (auto-updates dependencies)
   - OR run: `python main.py`

4. **Configure API Keys**
   - Same as Option 1 steps 3-4

### Advantages
- Works on all Python versions (3.11+)
- Full system audio loopback support
- Easy to debug and modify
- PyAudioWPatch support (system audio transcription)

---

## Option 3: Manual Python Execution

```powershell
# Navigate to project folder
cd "D:\inter help\Interview-Cracker"

# Install requirements once
pip install -r requirements.txt

# Run the app
python main.py
```

---

## Features

### 🎤 Transcription
- Record audio from microphone or system speakers
- Powered by Azure Cognitive Services Speech-to-Text
- Automatically sends recognized text to AI for analysis

### 🤖 AI Assistant (Gemini)
- Responds to your transcribed questions
- Fallback support for multiple Gemini models
- Supports system prompts and custom instructions
- Includes your resume/context for interview prep

### 📸 Screenshot Analysis
- Hotkey: **Alt+X** to capture screen
- Sends to Gemini for analysis
- Useful for: coding help, UI analysis, text extraction

### ⚙️ Customization
- Change AI model (2.0-flash, 1.5-pro, etc.)
- Add custom instructions
- Control microphone vs. system audio
- Hide from taskbar and screen sharing

---

## API Key Sources

### Azure Speech (Free Tier Available)
1. Go to https://portal.azure.com
2. Create "Cognitive Services" resource
3. Select "Speech" service
4. Copy API Key from Keys section
5. Copy Region (e.g., `eastus`)

### Google Gemini (Free Tier - 60 calls/minute)
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Paste in Settings → 🔑 API Keys

---

## Performance & Storage

- **EXE Size**: ~122 MB
- **Memory Usage**: ~400-600 MB while running
- **Internet Required**: Yes (for Azure & Gemini APIs)
- **Offline Support**: No (requires cloud APIs)

---

## Support & Issues

If you encounter problems:

1. **Check the Status Bar** (bottom of app)
   - Shows error messages and diagnostics
   - Watch for warnings about audio/API issues

2. **Check Terminal Output** (if running from Python)
   - Detailed error messages and stack traces
   - Look for "Error:", "Failed:", or "Exception"

3. **Restart the App**
   - Close completely
   - Reopen and try again

4. **Verify API Keys**
   - Make sure keys are not expired
   - Test keys in respective portals
   - Ensure correct region for Azure

---

## File Structure

```
Interview-Cracker/
├── main.py                      # Entry point
├── requirements.txt             # Python dependencies
├── RUN_ME.bat                   # Easy launcher for Windows
├── styles.qss                   # GUI styling
├── src/
│   ├── config.py               # Configuration & env vars
│   ├── core/
│   │   ├── audio.py            # Audio capture & transcription
│   │   └── gemini.py           # AI responses
│   ├── ui/
│   │   ├── main_window.py      # Main GUI window
│   │   └── widgets.py          # Custom Qt widgets
│   └── utils/
│       └── helpers.py          # Utility functions
└── dist/
    └── AI-Assistant.exe         # Standalone executable
```

---

## License & Attribution

This project uses:
- **PyQt6** for GUI
- **Azure Cognitive Services** for speech
- **Google Gemini** for AI responses
- **PyAudio** for audio capture
- See `requirements.txt` for full list
