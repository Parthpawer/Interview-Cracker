import sys
import os
import time
import io
import threading
import ctypes
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, 
    QPushButton, QTextEdit, QTabWidget, QLineEdit, QScrollArea,
    QSystemTrayIcon, QMenu, QApplication, QStyle
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QPoint, QRect, QTimer
from PyQt6.QtGui import QTextCursor, QMouseEvent, QCursor, QIcon, QShortcut, QKeySequence
from PIL import ImageGrab
from pynput import keyboard

from src.config import Config
from src.core.audio import AudioTranscriber
from src.core.gemini import GeminiClient
from src.ui.widgets import CustomComboBox
from src.utils.helpers import markdown_to_html, resource_path

class TranscriptionSignals(QObject):
    """Signals for thread-safe GUI updates"""
    transcription_update = pyqtSignal(str)
    status_update = pyqtSignal(str)
    screenshot_signal = pyqtSignal()
    restore_window_signal = pyqtSignal()
    add_user_message = pyqtSignal(str)
    add_screenshot_message = pyqtSignal()
    add_assistant_message_start = pyqtSignal()
    add_assistant_chunk = pyqtSignal(str)
    toggle_visibility_signal = pyqtSignal()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.chunk_buffer = []
        self.last_ui_update = time.time()
        self.update_timer = None
        self.buffer_text = ""
        self.batch_timer = QTimer(self)
        self.batch_timer.setInterval(1200) # Reduced from 2s to 1.2s for faster response
        self.batch_timer.setSingleShot(True)
        self.batch_timer.timeout.connect(self._flush_transcription_buffer)
        
        self.setWindowTitle(Config.APP_TITLE)
        self.resize(Config.DEFAULT_WIDTH, Config.DEFAULT_HEIGHT)
        self.setMinimumSize(Config.MIN_WIDTH, Config.MIN_HEIGHT)
        
        # Frameless window with stay on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Drag and resize tracking
        self.dragging = False
        self.drag_position = QPoint()
        
        self.resizing = False
        self.resize_edge = None
        self.resize_start_pos = None
        self.resize_start_geo = None
        self.border_width = 8
        
        self.setMouseTracking(True)
        self.setWindowOpacity(0.95)
        
        # Load Styles
        self.load_styles()
        
        # Setup UI
        self.setup_ui()
        self.setup_system_tray()
        
        # Initialize Core Modules
        self.signals = TranscriptionSignals()
        self.connect_signals()
        
        self.audio_transcriber = AudioTranscriber(self.signals)
        self.gemini_client = GeminiClient()
        
        # Windows API
        self.hwnd = None
        self.user32 = ctypes.windll.user32
        self.WDA_NONE = 0x00
        self.WDA_EXCLUDEFROMCAPTURE = 0x11
        
        # State
        self.current_assistant_message = ""
        self.current_screenshot_bytes = None
        self.ai_mode_on = False
        self.is_hidden = False
        
        self.toggle_shortcut = QShortcut(QKeySequence("Alt+W"), self)
        self.toggle_shortcut.activated.connect(self.toggle_visibility)
        
        self.setup_hotkey()
        self.showEvent = self._on_show

    def load_styles(self):
        """Load QSS styles from file."""
        try:
            style_path = resource_path(os.path.join('assets', 'styles.qss'))
            if os.path.exists(style_path):
                with open(style_path, 'r') as f:
                    self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Error loading styles: {e}")

    def setup_ui(self):
        """Initialize the user interface."""
        # Main container
        container = QWidget()
        container.setProperty("class", "main-container")
        
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(container)
        self.setLayout(outer_layout)

        main_layout = QHBoxLayout(container)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Left side - Chat
        chat_container = QWidget()
        chat_container.setMinimumWidth(400)
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(15, 15, 15, 15)
        
        # Title bar
        title_bar_widget = QWidget()
        title_bar_widget.setProperty("class", "title-bar")
        title_bar_layout = QHBoxLayout(title_bar_widget)
        title_bar_layout.setContentsMargins(12, 8, 12, 8)
        
        title_bar = QLabel("🤖 AI Assistant")
        title_bar.setProperty("class", "title-label")
        
        minimize_btn = QPushButton("−")
        minimize_btn.setFixedSize(30, 30)
        minimize_btn.setProperty("class", "window-control-btn")
        minimize_btn.clicked.connect(self.showMinimized)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setProperty("class", "window-control-btn close-btn")
        close_btn.clicked.connect(self.close)
        
        title_bar_layout.addWidget(title_bar)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(minimize_btn)
        title_bar_layout.addWidget(close_btn)
        
        # Make title bar draggable
        title_bar_widget.mousePressEvent = self.title_mouse_press
        title_bar_widget.mouseMoveEvent = self.title_mouse_move
        title_bar_widget.mouseReleaseEvent = self.title_mouse_release
        self.title_bar_widget = title_bar_widget
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("💬 Chat with AI will appear here...")
        self.chat_display.setProperty("class", "chat-display")
        
        control_bar = QWidget()
        control_bar.setProperty("class", "control-bar")
        control_layout = QHBoxLayout(control_bar)
        
        self.transcribe_button = QPushButton("🎤 Start Transcription")
        self.transcribe_button.setProperty("class", "transcribe-btn")
        
        # Audio source toggle button
        self.audio_source_button = QPushButton("🎤 System Audio")
        self.audio_source_button.setProperty("class", "audio-source-btn")
        self.audio_source_button.setCheckable(True)
        self.audio_source_button.setChecked(False)  # False = System Audio, True = Microphone
        self.audio_source_button.clicked.connect(self.toggle_audio_source)
        self.audio_source_button.setFixedHeight(36)
        self.audio_source_button.setFixedWidth(120)
        
        self.ai_mode_button = QPushButton("AI Mode: OFF ❌")
        self.ai_mode_button.setProperty("class", "ai-mode-btn")
        self.ai_mode_button.clicked.connect(self.toggle_ai_mode)
        self.ai_mode_button.setFixedHeight(36)
        self.ai_mode_button.setFixedWidth(160)
        
        self.status_label = QLabel("Ready | Press Alt+X for screenshot")
        self.status_label.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        
        control_layout.addWidget(self.transcribe_button)
        control_layout.addWidget(self.audio_source_button)
        control_layout.addWidget(self.ai_mode_button)
        control_layout.addWidget(self.status_label)
        control_layout.addStretch()
        
        chat_layout.addWidget(title_bar_widget)
        chat_layout.addWidget(self.chat_display, stretch=1)
        chat_layout.addWidget(control_bar)

        # Right side - Settings
        settings_container = QWidget()
        settings_container.setMaximumWidth(400)
        settings_container.setMinimumWidth(250)
        settings_container.setProperty("class", "settings-container")
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        
        settings_title = QLabel("⚙️ Settings")
        settings_title.setProperty("class", "settings-title")
        
        settings_tabs = QTabWidget()
        
        # Tab 1: API Keys
        api_tab = QWidget()
        api_layout = QVBoxLayout(api_tab)
        api_layout.setSpacing(10)
        
        api_layout.addWidget(QLabel("Azure Speech API Keys (Comma Separated):"))
        self.azure_key_input = QTextEdit()
        self.azure_key_input.setPlaceholderText("Enter Azure API keys (e.g. key1,key2)...")
        self.azure_key_input.setMaximumHeight(80)
        
        # We process it out of the Config as a comma separated string
        azure_keys_str = ",".join(Config.SPEECH_KEYS) if Config.SPEECH_KEYS else ""
        self.azure_key_input.setPlainText(azure_keys_str)
        api_layout.addWidget(self.azure_key_input)
        
        api_layout.addWidget(QLabel("Azure Region:"))
        self.azure_region_input = QLineEdit()
        self.azure_region_input.setPlaceholderText("e.g., eastus")
        self.azure_region_input.setText(Config.SPEECH_REGION)
        api_layout.addWidget(self.azure_region_input)
        
        api_layout.addWidget(QLabel("Gemini API Keys (Comma Separated):"))
        self.gemini_key_input = QTextEdit()
        self.gemini_key_input.setPlaceholderText("Enter Gemini API keys (e.g. key1,key2)...")
        self.gemini_key_input.setMaximumHeight(80)
        
        gemini_keys_str = ",".join(Config.GEMINI_API_KEYS) if Config.GEMINI_API_KEYS else ""
        self.gemini_key_input.setPlainText(gemini_keys_str)
        api_layout.addWidget(self.gemini_key_input)
        
        save_keys_btn = QPushButton("💾 Save API Keys")
        save_keys_btn.clicked.connect(self.save_api_keys)
        api_layout.addWidget(save_keys_btn)
        
        test_keys_btn = QPushButton("🧪 Test Gemini Keys")
        test_keys_btn.clicked.connect(self.test_gemini_keys)
        api_layout.addWidget(test_keys_btn)
        
        api_layout.addStretch()
        
        # Tab 2: Model & Prompt
        model_tab = QWidget()
        model_layout = QVBoxLayout(model_tab)
        model_layout.setSpacing(10)
        
        model_layout.addWidget(QLabel("Gemini Model:"))
        self.model_selector = CustomComboBox()
        self.model_selector.addItems([
            "gemini-2.0-flash",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash-8b"
        ])
        self.model_selector.setCurrentText(Config.GEMINI_MODEL)
        self.model_selector.currentTextChanged.connect(self.on_model_changed)
        model_layout.addWidget(self.model_selector)
        
        model_layout.addWidget(QLabel("Additional Instructions:"))
        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setPlaceholderText("Add extra instructions...")
        if Config.SYSTEM_PROMPT:
            self.system_prompt_input.setPlainText(Config.SYSTEM_PROMPT)
        self.system_prompt_input.setMaximumHeight(100)
        model_layout.addWidget(self.system_prompt_input)
        
        update_prompt_btn = QPushButton("✅ Update Instructions")
        update_prompt_btn.clicked.connect(self.update_system_prompt)
        model_layout.addWidget(update_prompt_btn)
        
        model_layout.addStretch()
        
        # Tab 3: Privacy
        privacy_tab = QWidget()
        privacy_layout = QVBoxLayout(privacy_tab)
        privacy_layout.setSpacing(15)
        
        self.taskbar_toggle = QCheckBox("Hide from Taskbar")
        self.screenshare_toggle = QCheckBox("Hide from Screen Sharing")
        
        privacy_layout.addWidget(self.taskbar_toggle)
        privacy_layout.addWidget(self.screenshare_toggle)
        privacy_layout.addWidget(QLabel("✅ Dropdowns will be hidden\nwhen screen sharing is enabled."))
        privacy_layout.addStretch()
        
        settings_tabs.addTab(api_tab, "🔑 API Keys")
        settings_tabs.addTab(model_tab, "🤖 AI Config")
        settings_tabs.addTab(privacy_tab, "🔒 Privacy")
        
        settings_layout.addWidget(settings_title)
        settings_layout.addWidget(settings_tabs)
        settings_layout.addStretch()

        main_layout.addWidget(chat_container, stretch=7)
        main_layout.addWidget(settings_container, stretch=3)

        self.taskbar_toggle.stateChanged.connect(self.toggle_taskbar)
        self.screenshare_toggle.stateChanged.connect(self.toggle_screenshare)
        self.transcribe_button.clicked.connect(self.toggle_transcription)

    def setup_system_tray(self):
        """Initialize the system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        
        tray_menu = QMenu()
        
        restore_action = tray_menu.addAction("Show/Restore Window")
        restore_action.triggered.connect(self.restore_window)
        
        toggle_action = tray_menu.addAction("Toggle Transcription")
        toggle_action.triggered.connect(self.toggle_transcription)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.instance().quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        """Handle system tray icon clicks."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.restore_window()

    def connect_signals(self):
        """Connect signals to slots."""
        self.signals.transcription_update.connect(self.update_transcription)
        self.signals.status_update.connect(self.update_status)
        self.signals.screenshot_signal.connect(self.take_screenshot_safe)
        self.signals.restore_window_signal.connect(self.restore_window)
        self.signals.toggle_visibility_signal.connect(self.toggle_visibility)
        self.signals.add_user_message.connect(self.add_user_message_to_chat)
        self.signals.add_screenshot_message.connect(self.add_screenshot_message_to_chat)
        self.signals.add_assistant_message_start.connect(self.start_assistant_message)
        self.signals.add_assistant_chunk.connect(self.add_assistant_chunk)

    def save_api_keys(self):
        """Save API keys."""
        azure_keys = self.azure_key_input.toPlainText().strip()
        azure_region = self.azure_region_input.text().strip()
        gemini_keys = self.gemini_key_input.toPlainText().strip()
        
        success, message = Config.save_env(speech_keys=azure_keys, speech_region=azure_region, gemini_keys=gemini_keys)
        self.signals.status_update.emit(message)
        
        if gemini_keys:
            # Update current session with the newly inputted keys parsing them as lists
            self.gemini_client.api_keys = [k.strip() for k in gemini_keys.split(',')]
            self.gemini_client.current_key_index = 0
            self.gemini_client._initialize_client()

    def toggle_ai_mode(self):
        """Toggle Gemini AI mode on/off."""
        self.ai_mode_on = not self.ai_mode_on
        if self.ai_mode_on:
            self.ai_mode_button.setText("AI Mode: ON 🤖")
            self.signals.status_update.emit("AI Mode enabled")
        else:
            self.ai_mode_button.setText("AI Mode: OFF ❌")
            self.signals.status_update.emit("AI Mode disabled")

    def toggle_audio_source(self):
        """Toggle between system audio and microphone input."""
        if self.audio_source_button.isChecked():
            self.audio_source_button.setText("🎤 Microphone")
            self.signals.status_update.emit("Audio source set to Microphone")
        else:
            self.audio_source_button.setText("🎤 System Audio")
            self.signals.status_update.emit("Audio source set to System Audio")

    def on_model_changed(self, model_name):
        """Handle model change."""
        self.gemini_client.update_model(model_name)
        Config.save_env(gemini_model=model_name)
        self.signals.status_update.emit(f"✅ Model: {model_name} (saved)")

    def update_system_prompt(self):
        """Update system prompt."""
        instructions = self.system_prompt_input.toPlainText().strip()
        self.gemini_client.update_instructions(instructions)
        Config.save_env(system_prompt=instructions)
        self.signals.status_update.emit("✅ Instructions updated and saved")
    def test_gemini_keys(self):
        """Test Gemini API keys."""
        gemini_keys = self.gemini_key_input.toPlainText().strip()
        if not gemini_keys:
            self.signals.status_update.emit("❌ No Gemini API keys provided")
            return
        
        # Temporarily update keys for testing
        original_keys = self.gemini_client.api_keys
        self.gemini_client.api_keys = [k.strip() for k in gemini_keys.split(',') if k.strip()]
        self.gemini_client.current_key_index = 0
        self.gemini_client.client = None
        self.gemini_client.chat = None
        
        def test_worker():
            try:
                # Try a simple test message
                response = self.call_gemini_with_keys("Hello, test message.")
                # Consume the response
                chunks = list(response)
                self.signals.status_update.emit("✅ Gemini API keys are working!")
            except Exception as e:
                error_msg = str(e)
                # Use specific error messages from optimized Gemini client
                if "Gemini API not configured" in error_msg:
                    display_msg = "❌ Invalid or empty API keys"
                elif "quota exceeded" in error_msg.lower():
                    display_msg = "❌ API quota exceeded. Please wait a few minutes and try again."
                elif "temporarily unavailable" in error_msg.lower():
                    display_msg = "❌ Gemini service temporarily unavailable. Please try again shortly."
                elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                    display_msg = f"❌ {error_msg}"
                else:
                    display_msg = f"❌ API test failed: {error_msg}"
                
                self.signals.status_update.emit(display_msg)
            finally:
                # Restore original keys
                self.gemini_client.api_keys = original_keys
                self.gemini_client.current_key_index = 0
                self.gemini_client.client = None
                self.gemini_client.chat = None
        
        threading.Thread(target=test_worker, daemon=True).start()
    def toggle_transcription(self):
        """Toggle transcription state."""
        if not self.audio_transcriber.is_transcribing:
            api_keys = self.azure_key_input.toPlainText()
            if not api_keys and Config.SPEECH_KEYS:
                 api_keys = ",".join(Config.SPEECH_KEYS)
            region = self.azure_region_input.text() or Config.SPEECH_REGION
            
            # Get audio source selection: False = System Audio, True = Microphone
            use_microphone = self.audio_source_button.isChecked()
            
            if self.audio_transcriber.start(api_keys, region, use_microphone):
                self.transcribe_button.setText("⏹ Stop Transcription")
                self.transcribe_button.setProperty("class", "transcribe-btn-active")
                self.transcribe_button.style().unpolish(self.transcribe_button)
                self.transcribe_button.style().polish(self.transcribe_button)
        else:
            self.audio_transcriber.stop()
            self.batch_timer.stop()
            
            buffered_text = self.buffer_text.strip()
            self.buffer_text = ""
            
            if self.ai_mode_on and buffered_text:
                self.signals.status_update.emit("🤖 Thinking...")
                self.send_to_gemini(buffered_text)
            else:
                self.signals.status_update.emit("Status: Stopped | Press Alt+X for screenshot")
            
            self.transcribe_button.setText("🎤 Start Transcription")
            self.transcribe_button.setProperty("class", "transcribe-btn")
            self.transcribe_button.style().unpolish(self.transcribe_button)
            self.transcribe_button.style().polish(self.transcribe_button)

    def update_transcription(self, text):
        """Handle transcribed text."""
        if text.startswith("✅"):
            clean_text = text.replace("✅", "").strip()
            if clean_text:
                if self.buffer_text:
                    self.buffer_text += " " + clean_text
                else:
                    self.buffer_text = clean_text
                self.batch_timer.start()
                self.signals.status_update.emit("Status: Listening...")

    def _flush_transcription_buffer(self):
        # We now allow auto-flushing while transcribing to reduce buffer delay.

        if not self.buffer_text:
            return

        text_to_send = self.buffer_text.strip()
        self.buffer_text = ""

        if not self.ai_mode_on:
            self.signals.status_update.emit("AI Mode is OFF — transcription preserved only")
            return

        if len(text_to_send) <= 5 and "?" not in text_to_send:
            self.signals.status_update.emit("Short phrase detected — continuing to buffer...")
            return

        self.send_to_gemini(text_to_send)

    def send_to_gemini(self, text):
        """Send text to Gemini with background threading and fast response model."""
        if not self.ai_mode_on:
            self.signals.status_update.emit("AI Mode is OFF — Gemini will not process transcription")
            return
        if not self.gemini_client.api_keys:
            self.signals.status_update.emit("Error: Gemini API not configured")
            return

        trimmed_text = text.strip()[-3000:]
        self.signals.status_update.emit("🤖 Thinking...")

        def gemini_worker():
            try:
                self.signals.add_user_message.emit(text)
                self.signals.add_assistant_message_start.emit()

                response = self.call_gemini_with_keys(trimmed_text)
                
                for chunk in response:
                    if hasattr(chunk, 'text') and chunk.text:
                        self.signals.add_assistant_chunk.emit(chunk.text)

                if self.chunk_buffer:
                    QTimer.singleShot(0, self._render_assistant_message_safe)
            except Exception as e:
                error_msg = str(e)
                
                # Use specific error messages from optimized Gemini client
                if "Gemini API not configured" in error_msg:
                    display_msg = "⚠️ Gemini API not configured. Please add API keys in Settings."
                elif "quota exceeded" in error_msg.lower():
                    display_msg = "⚠️ API quota exceeded. Please try again in a few minutes."
                elif "temporarily unavailable" in error_msg.lower():
                    display_msg = "⚠️ Gemini service temporarily unavailable. Please try again shortly."
                elif "Unable to reach Gemini" in error_msg:
                    display_msg = "⚠️ Unable to reach Gemini API. Please check your connection or try again later."
                elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                    display_msg = f"⚠️ {error_msg}"
                else:
                    # Fallback to actual error message if available
                    display_msg = error_msg if error_msg.startswith("⚠️") or error_msg.startswith("❌") else f"⚠️ {error_msg}"
                
                self.signals.status_update.emit(display_msg)
                self.signals.add_assistant_chunk.emit(display_msg)
                if self.chunk_buffer:
                    QTimer.singleShot(0, self._render_assistant_message_safe)

        threading.Thread(target=gemini_worker, daemon=True).start()

    def call_gemini_with_keys(self, text):
        """Call Gemini using multiple API keys with round-robin and failover."""
        if not self.gemini_client.api_keys:
            raise Exception("Gemini API not configured")

        model_name = self.gemini_client.current_model or Config.GEMINI_MODEL
        return self.gemini_client.send_message_stream(text, model_name=model_name)

    def setup_hotkey(self):
        """Setup global hotkey."""
        def on_screenshot_hotkey():
            self.signals.screenshot_signal.emit()

        def on_toggle_visibility_hotkey():
            self.signals.toggle_visibility_signal.emit()
        
        self.hotkey_listener = keyboard.GlobalHotKeys({
            '<alt>+x': on_screenshot_hotkey,
            '<alt>+w': on_toggle_visibility_hotkey
        })
        self.hotkey_listener.start()

    def toggle_visibility(self):
        """Toggle window visibility with Alt+W."""
        if self.isVisible():
            self.is_hidden = True
            self.hide()
        else:
            self.is_hidden = False
            self.show()
            self.raise_()
            self.activateWindow()

    def take_screenshot_safe(self):
        """Thread-safe screenshot handler."""
        was_visible = self.isVisible()
        
        if was_visible:
            self.hide()
            time.sleep(0.3)
        
        threading.Thread(target=self._take_screenshot_thread, args=(was_visible,), daemon=True).start()

    def _take_screenshot_thread(self, was_visible):
        """Take screenshot in separate thread."""
        try:
            screenshot = ImageGrab.grab()
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='PNG')
            self.current_screenshot_bytes = img_byte_arr.getvalue()
            
            self.signals.add_screenshot_message.emit()
            if self.ai_mode_on:
                self.send_screenshot_to_gemini(self.current_screenshot_bytes)
                self.signals.status_update.emit("Screenshot captured and sent to AI")
            else:
                self.signals.status_update.emit("Screenshot captured — AI Mode is OFF")
        except Exception as e:
            self.signals.status_update.emit(f"Screenshot error: {str(e)}")
        finally:
            if was_visible:
                self.signals.restore_window_signal.emit()

    def send_screenshot_to_gemini(self, image_bytes):
        """Send screenshot to Gemini."""
        if not self.ai_mode_on:
            self.signals.status_update.emit("AI Mode is OFF — screenshot will not be sent to Gemini")
            return
        if not self.gemini_client.api_keys:
            self.signals.status_update.emit("Error: Gemini API not configured")
            return
        
        def gemini_screenshot_worker():
            try:
                self.signals.add_assistant_message_start.emit()
                response = self.gemini_client.send_screenshot_stream(image_bytes)
                
                for chunk in response:
                    if hasattr(chunk, 'text') and chunk.text:
                        self.signals.add_assistant_chunk.emit(chunk.text)
                
                if self.chunk_buffer:
                    QTimer.singleShot(0, self._render_assistant_message_safe)
                
            except Exception as e:
                error_msg = str(e)
                # Display specific error messages from optimized Gemini client
                if "quota exceeded" in error_msg.lower():
                    display_msg = "⚠️ API quota exceeded. Please try again in a few minutes."
                elif "temporarily unavailable" in error_msg.lower():
                    display_msg = "⚠️ Gemini service temporarily unavailable. Please try again shortly."
                elif "Unable to reach" in error_msg:
                    display_msg = "⚠️ Unable to reach Gemini API. Please check your connection or try again later."
                else:
                    display_msg = f"⚠️ {error_msg}" if not error_msg.startswith("⚠️") else error_msg
                
                self.signals.status_update.emit(display_msg)
        
        threading.Thread(target=gemini_screenshot_worker, daemon=True).start()

    def restore_window(self):
        """Restore window to front."""
        self.is_hidden = False
        self.show()
        self.raise_()
        self.activateWindow()
        
        if sys.platform == 'win32' and self.hwnd:
            HWND_TOPMOST = -1
            HWND_NOTOPMOST = -2
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_SHOWWINDOW = 0x0040
            
            self.user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
            self.user32.SetWindowPos(self.hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        
        flags = self.windowFlags()
        if not (flags & Qt.WindowType.WindowStaysOnTopHint):
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
            self.show()

    # --- UI Update Methods (Chat Bubbles) ---
    
    def add_user_message_to_chat(self, text):
        self.chat_display.append(f'''
            <br>
            <div style="margin: 15px 0; clear: both;">
                <div style="
                    color: #9cf7a5;
                    padding: 14px 18px;
                    border-radius: 12px;
                    word-wrap: break-word;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
                    font-size: 14px;
                    line-height: 1.6;
                    border: 1px solid #034d0a;
                    display: block;
                ">
                    <div style="margin-bottom: 6px; font-weight: 600; color: #6fe07d; font-size: 12px;">🎤 You</div>
                    <div style="color: #9cf7a5;">{text}</div>
                </div>
            </div>
            <br>
        ''')
        self.scroll_to_bottom()

    def add_screenshot_message_to_chat(self):
        self.chat_display.append(f'''
            <div style="margin: 15px 0; clear: both;">
                <div style="
                    color: #9cf7a5;
                    padding: 14px 18px;
                    border-radius: 12px;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
                    font-size: 14px;
                    line-height: 1.6;
                    border: 1px solid #034d0a;
                    display: block;
                ">
                    <div style="margin-bottom: 6px; font-weight: 600; color: #6fe07d; font-size: 12px;">📸 You</div>
                    <div style="color: #9cf7a5;">Screenshot shared</div>
                </div>
            </div>
            <br />
        ''')
        self.scroll_to_bottom()

    def start_assistant_message(self):
        self.current_assistant_message = ""
        self.assistant_message_start_pos = len(self.chat_display.toPlainText())
        
        self.chat_display.append(f'''
            <div style="margin: 15px 0; clear: both;">
                <div style="
                    color: #FFFFFF;
                    padding: 14px 18px;
                    border-radius: 12px;
                    word-wrap: break-word;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
                    font-size: 14px;
                    line-height: 1.6;
                    border: 1px solid #5d1619;
                    display: block;
                ">
                    <div style="margin-bottom: 6px; font-weight: 600; color: #ff9597; font-size: 12px;">🤖 AI Assistant</div>
                    <div style="color: #FFFFFF;"><span id="asst_content_placeholder"></span></div>
                </div>
            </div>
            <br />
        ''')
        self.scroll_to_bottom()

    def add_assistant_chunk(self, chunk):
        self.chunk_buffer.append(chunk)
        current_time = time.time()
        if current_time - self.last_ui_update > 0.15 or len(self.chunk_buffer) > 8:
            self._render_assistant_message_safe()

    def _render_assistant_message_safe(self):
        if not self.chunk_buffer:
            return
        
        self.current_assistant_message += ''.join(self.chunk_buffer)
        self.chunk_buffer = []
        self.last_ui_update = time.time()
        
        html_content = markdown_to_html(self.current_assistant_message)
        
        cursor = self.chat_display.textCursor()
        cursor.setPosition(self.assistant_message_start_pos)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        
        cursor.insertHtml(f'''
            <div style="margin: 12px 0; display: block;">
                <div style="
                    color: #FFFFFF;
                    padding: 14px 18px;
                    border-radius: 12px;
                    word-wrap: break-word;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
                    font-size: 14px;
                    line-height: 1.6;
                    border: 1px solid #5d1619;
                ">
                    <div style="margin-bottom: 6px; font-weight: 600; color: #ff9597; font-size: 12px;">🤖 AI Assistant</div>
                    <div style="color: #FFFFFF;">{html_content}</div>
                </div>
                <br>
            </div>
        ''')
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_status(self, status):
        self.status_label.setText(status)

    # --- Window Management ---

    def title_mouse_press(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def title_mouse_move(self, event: QMouseEvent):
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def title_mouse_release(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self.get_resize_edge(event.pos())
            if edge:
                self.resizing = True
                self.resize_edge = edge
                self.resize_start_pos = event.globalPosition().toPoint()
                self.resize_start_geo = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.resizing and self.resize_edge:
            self.resize_window(event.globalPosition().toPoint())
            event.accept()
        else:
            edge = self.get_resize_edge(event.pos())
            self.update_cursor_shape(edge)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.resizing = False
            self.resize_edge = None
            self.resize_start_pos = None
            self.resize_start_geo = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        super().mouseReleaseEvent(event)

    def get_resize_edge(self, pos):
        rect = self.rect()
        bw = self.border_width
        
        on_left = pos.x() <= bw
        on_right = pos.x() >= rect.width() - bw
        on_top = pos.y() <= bw
        on_bottom = pos.y() >= rect.height() - bw
        
        if on_top and on_left: return 'top-left'
        elif on_top and on_right: return 'top-right'
        elif on_bottom and on_left: return 'bottom-left'
        elif on_bottom and on_right: return 'bottom-right'
        elif on_left: return 'left'
        elif on_right: return 'right'
        elif on_top: return 'top'
        elif on_bottom: return 'bottom'
        return None

    def update_cursor_shape(self, edge):
        if edge in ['top', 'bottom']: self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edge in ['left', 'right']: self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edge in ['top-left', 'bottom-right']: self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edge in ['top-right', 'bottom-left']: self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else: self.setCursor(Qt.CursorShape.ArrowCursor)

    def resize_window(self, global_pos):
        if not self.resize_start_geo or not self.resize_start_pos: return
        
        delta = global_pos - self.resize_start_pos
        geo = QRect(self.resize_start_geo)
        
        if 'left' in self.resize_edge:
            new_left = geo.left() + delta.x()
            new_width = geo.width() - delta.x()
            if new_width >= self.minimumWidth(): geo.setLeft(new_left)
        
        if 'right' in self.resize_edge:
            new_width = geo.width() + delta.x()
            if new_width >= self.minimumWidth(): geo.setRight(geo.right() + delta.x())
        
        if 'top' in self.resize_edge:
            new_top = geo.top() + delta.y()
            new_height = geo.height() - delta.y()
            if new_height >= self.minimumHeight(): geo.setTop(new_top)
        
        if 'bottom' in self.resize_edge:
            new_height = geo.height() + delta.y()
            if new_height >= self.minimumHeight(): geo.setBottom(geo.bottom() + delta.y())
        
        if geo.width() >= self.minimumWidth() and geo.height() >= self.minimumHeight():
            self.setGeometry(geo)

    def _on_show(self, event):
        self.hwnd = self.user32.FindWindowW(None, self.windowTitle())

    def toggle_taskbar(self):
        if self.taskbar_toggle.isChecked():
            self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self.show()
        else:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self.show()

    def toggle_screenshare(self):
        if not self.hwnd:
            self.hwnd = self.user32.FindWindowW(None, self.windowTitle())

        if self.hwnd:
            if self.screenshare_toggle.isChecked():
                self.user32.SetWindowDisplayAffinity(self.hwnd, self.WDA_EXCLUDEFROMCAPTURE)
                self.model_selector.set_screen_share_hidden(True)
            else:
                self.user32.SetWindowDisplayAffinity(self.hwnd, self.WDA_NONE)
                self.model_selector.set_screen_share_hidden(False)

    def closeEvent(self, event):
        if self.audio_transcriber.is_transcribing:
            self.audio_transcriber.stop()
        
        if hasattr(self, 'hotkey_listener'):
            self.hotkey_listener.stop()
            
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        
        event.accept()
