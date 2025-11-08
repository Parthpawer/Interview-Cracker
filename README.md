# 🧠 AI-Assistant Desktop Application

**AI-Assistant** is a Windows desktop application combining **real-time audio transcription**, **screenshot-based context sharing**, and **conversational AI** via **Gemini** and **Azure Speech APIs**.  
Built with **Python** and **PyQt6**, it integrates advanced cloud and local AI models to boost productivity and accessibility.

---

## 🚀 Features

- 🎙️ **Live Audio Transcription:** Capture system audio and transcribe it using Azure Cognitive Services with real-time updates.
- 🖼️ **Screenshot-to-Insight:** Share desktop screenshots and receive contextual help or explanations from Gemini AI.
- 💬 **Conversational Chat:** Chat-like interface for smooth interaction with AI and live transcriptions.
- ⚡ **Streamed Responses:** Get assistant replies instantly with streaming output.
- ⌨️ **Hotkeys & Controls:** Easily start/stop transcription, take screenshots, or manage messages.
- 🔐 **API Flexibility:** Configure Azure & Gemini API keys and models via UI or `.env`.
- 🧩 **Rich Media Support:** Handles system audio, screenshots, markdown replies, and themed UI.
- 📦 **Windows Packaging:** Ready-to-deploy executable built using PyInstaller.

---

## 🧩 Installation

### 1. Clone the Repository

```bash
git clone <repo-url>
cd ai-assistant
```

### 2. Install Requirements

```bash
pip install -r requirements.txt
```

Ensure the following packages are included:
- `azure-cognitiveservices-speech`
- `google-genai`
- `PyQt6`
- `pyaudio`
- `numpy`
- `scipy`
- `python-dotenv`
- `Pillow`

### 3. Configuration

Create a `.env` file with the following credentials:

```env
SPEECH_KEY=your-azure-key
SPEECH_REGION=your-azure-region
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=your-model-choice
```

Alternatively, configure these within the app’s settings UI.

### 4. Build Executable (Windows)

To package the application:

```bash
pyinstaller AI-Assistant.spec
```

or

```bash
pyinstaller file.spec
```

The final executable and dependencies will be bundled under the `dist/` folder.

---

## 🧠 Usage

| Action | Description |
|--------|--------------|
| **Start/Stop Transcription** | Toggle real-time audio transcription |
| **Send Screenshot** | Use hotkey `Alt+X` to capture and send a screenshot |
| **Chat Interaction** | View AI responses and transcription history |
| **Settings** | Update API keys, model preferences, and app configuration |

Run directly from the source:

```bash
python index.py
```

---

## 📂 Project Structure

| File/Folder | Description |
|--------------|--------------|
| `index.py` | Core app logic — UI, audio handling, and AI integration |
| `AI-Assistant.spec` | PyInstaller config for building the executable |
| `file.spec` | Alternative build configuration |
| `.env` | Environment credentials for APIs |
| `requirements.txt` | Python dependencies list |

---

## 🏗️ Architecture Overview

### Core Components
- **Audio Capture:** WASAPI loopback for system-level recording  
- **Speech-to-Text:** Azure Cognitive Services  
- **AI Backend:** Google Gemini for contextual and creative responses  
- **UI Framework:** PyQt6 for GUI design and interaction  
- **Packaging:** PyInstaller for one-click Windows deployment  

### Key Libraries
- `azure-cognitiveservices-speech` — Speech recognition  
- `google-genai` — Gemini AI integration  
- `PyQt6` — GUI framework  
- `pyaudio` — Audio input/output handling  
- `numpy`, `scipy` — Audio signal processing  
- `Pillow` — Image processing  

---

## ⚙️ Configuration Options

You can customize API credentials through `.env` or UI:

```env
SPEECH_KEY=<Azure Speech API Key>
SPEECH_REGION=<Azure Speech Region>
GEMINI_API_KEY=<Google Gemini API Key>
GEMINI_MODEL=<Model name>
```

For advanced customization:
- Modify logic in `index.py`
- Adjust packaging via `.spec` files
- Add themes or icons by editing resource configs

---

## 🧰 Troubleshooting

### Audio Issues
- Ensure **WASAPI loopback** is enabled in Windows Sound settings.
- Verify microphone and audio device permissions.

### API Errors
- Check if API keys are valid and active.
- Ensure `.env` is properly formatted.
- Confirm correct **region** for Azure Speech API.

### Build Problems
- Run from the project’s root directory.
- Update dependencies:  
  ```bash
  pip install --upgrade pyinstaller
  ```
- Ensure all modules in `requirements.txt` are installed.

---

## 🧑‍💻 Development

Run app locally:

```bash
python index.py
```

Build for Windows:

```bash
pyinstaller AI-Assistant.spec
```

Executable output:  
`dist/AI-Assistant/AI-Assistant.exe`

---

## 🤝 Contributing

Contributions are welcome!  
To contribute:

1. Fork this repo  
2. Create a feature branch  
   ```bash
   git checkout -b feature/your-feature
   ```
3. Commit changes  
   ```bash
   git commit -m "Add new feature"
   ```
4. Push and open a **Pull Request**

---

## 📜 License

This project is licensed under the **MIT License** (or specify another if preferred).

---

## 🧩 Credits

This project leverages:

- **Microsoft Azure Cognitive Services** — Speech recognition  
- **Google Gemini API** — Conversational intelligence  
- **PyQt6** — Cross-platform GUI  
- **PyAudio**, **NumPy**, **SciPy**, **Pillow** — Core utilities and processing tools  

---

## 🕒 Changelog

### Version 1.0.0 (Initial Release)
- Added live Azure Speech transcription  
- Integrated Gemini AI for conversation and screenshot insights  
- Implemented PyQt chat interface  
- Added streaming responses  
- Enabled `.env` and UI-based API configuration  
- Packaged for Windows distribution  

---

## 📬 Support

For bug reports, feature requests, or suggestions:
- Open an **Issue** on the GitHub repository  
- Or contact the maintainers directly

---

✨ *Developed with Python to enhance desktop productivity.*
