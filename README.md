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
- 🔄 **CI/CD:** Automated builds and releases via GitHub Actions.

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

The final executable will be in `dist/AI-Assistant.exe`.

---

## 🧠 Usage

| Action | Description |
|--------|--------------|
| **Toggle Transcription (Global)** | Start or stop the mic securely over ANY window globally with `Alt + M` |
| **Send Context Snapshot** | Instantly snapshot your desktop to Gemini for analysis with `Alt + X` |
| **Stealth Mode** | Completely hide/restore the app visually from the desktop with `Alt + A` |
| **Hardware Privacy Check** | Toggle Taskbar and Screen-Sharing hardware protections with `Alt + Z` |
| **Settings UI** | Configure API keys natively routing securely to a local `.env` file |

Run directly from the source:

```bash
python main.py
```

---

## 📂 Project Structure

| File/Folder | Description |
|--------------|--------------|
| `main.py` | Entry point of the application |
| `src/` | Source code directory |
| `src/core/` | Business logic (Audio, Gemini) |
| `src/ui/` | User Interface logic and styling routines |
| `assets/` | External stylesheets, icons, and dynamic datas |
| `tests/` | Developer scripts and debug testing handlers |
| `AI-Assistant.spec` | Customized PyInstaller AST asset compiler |
| `.github/workflows/` | CI/CD configurations |

---

## 🚀 CI/CD & Deployment

This project uses **GitHub Actions** for automated builds and releases.

### Automated Builds
Pushing to the `main` branch triggers a workflow that builds the Windows executable and uploads it as an artifact.

### Creating a Release
To publish a new version:
1.  Tag your commit: `git tag v1.0.0`
2.  Push the tag: `git push origin v1.0.0`

GitHub will automatically build the app and create a **Release** with the `.exe` attached.

---

## 🏗️ Architecture Overview

### Core Components
- **Audio Capture:** WASAPI loopback for system-level recording
- **Speech-to-Text:** Azure Cognitive Services
- **AI Backend:** Google Gemini for contextual and creative responses
- **UI Framework:** PyQt6 for GUI design and interaction
- **Packaging:** PyInstaller for one-click Windows deployment

---

## 🤝 Contributing

Contributions are welcome!
1. Fork this repo
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit changes (`git commit -m "Add new feature"`)
4. Push and open a **Pull Request**

---

## 📜 License

This project is licensed under the **MIT License**.
