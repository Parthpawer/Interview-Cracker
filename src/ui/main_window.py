import sys
import os
import time
import io
import threading
import ctypes
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, 
    QPushButton, QTextEdit, QTabWidget, QLineEdit, QScrollArea,
    QDialog, QFormLayout, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QPoint, QRect, QTimer
from PyQt6.QtGui import QTextCursor, QMouseEvent, QCursor
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

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.chunk_buffer = []
        self.last_ui_update = time.time()
        self.update_timer = None
        
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
        self.setWindowOpacity(0.53)
        
        # Load Styles
        self.load_styles()
        
        # Setup UI
        self.setup_ui()
        
        # Show Startup Dialog
        QTimer.singleShot(100, self.show_startup_dialog)
        
        # Initialize Core Modules
        self.signals = TranscriptionSignals()
        self.connect_signals()
        
        self.audio_transcriber = AudioTranscriber(self.signals)
        self.gemini_client = GeminiClient()
        self.hwnd = None
        self.user32 = ctypes.windll.user32
        self.WDA_NONE = 0x00
        self.WDA_EXCLUDEFROMCAPTURE = 0x11
        
        # State
        self.current_assistant_message = ""
        self.current_screenshot_bytes = None
        
        self.setup_hotkey()
        self.showEvent = self._on_show

    def load_styles(self):
        """Load QSS styles from file."""
        try:
            style_path = resource_path('styles.qss')
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
        
        self.status_label = QLabel("Ready | Press Alt+X for screenshot")
        self.status_label.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        
        control_layout.addWidget(self.transcribe_button)
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
        
        api_layout.addWidget(QLabel("Azure Speech API Key:"))
        self.azure_key_input = QLineEdit()
        self.azure_key_input.setPlaceholderText("Enter Azure API key")
        self.azure_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.azure_key_input.setText(Config.SPEECH_KEY)
        api_layout.addWidget(self.azure_key_input)
        
        api_layout.addWidget(QLabel("Azure Region:"))
        self.azure_region_input = QLineEdit()
        self.azure_region_input.setPlaceholderText("e.g., eastus")
        self.azure_region_input.setText(Config.SPEECH_REGION)
        api_layout.addWidget(self.azure_region_input)
        
        api_layout.addWidget(QLabel("Gemini API Key:"))
        self.gemini_key_input = QLineEdit()
        self.gemini_key_input.setPlaceholderText("Enter Gemini API key")
        self.gemini_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key_input.setText(Config.GEMINI_API_KEY)
        api_layout.addWidget(self.gemini_key_input)
        
        save_keys_btn = QPushButton("💾 Save API Keys")
        save_keys_btn.clicked.connect(self.save_api_keys)
        api_layout.addWidget(save_keys_btn)
        
        api_layout.addStretch()
        
        # Tab 2: Model & Prompt
        model_tab = QWidget()
        model_layout = QVBoxLayout(model_tab)
        model_layout.setSpacing(10)
        
        model_layout.addWidget(QLabel("Gemini Model:"))
        self.model_selector = CustomComboBox()
        self.model_selector.addItems([
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ])
        self.model_selector.setCurrentText(Config.GEMINI_MODEL)
        self.model_selector.currentTextChanged.connect(self.on_model_changed)
        model_layout.addWidget(self.model_selector)
        
        model_layout.addWidget(QLabel("Additional Instructions:"))
        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setPlaceholderText("Add extra instructions...")
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

    def connect_signals(self):
        """Connect signals to slots."""
        self.signals.transcription_update.connect(self.update_transcription)
        self.signals.status_update.connect(self.update_status)
        self.signals.screenshot_signal.connect(self.take_screenshot_safe)
        self.signals.restore_window_signal.connect(self.restore_window)
        self.signals.add_user_message.connect(self.add_user_message_to_chat)
        self.signals.add_screenshot_message.connect(self.add_screenshot_message_to_chat)
        self.signals.add_assistant_message_start.connect(self.start_assistant_message)
        self.signals.add_assistant_chunk.connect(self.add_assistant_chunk)

    def save_api_keys(self):
        """Save API keys."""
        azure_key = self.azure_key_input.text().strip()
        azure_region = self.azure_region_input.text().strip()
        gemini_key = self.gemini_key_input.text().strip()
        
        success, message = Config.save_env(azure_key, azure_region, gemini_key)
        self.signals.status_update.emit(message)
        
        if gemini_key:
            self.gemini_client.initialize()

    def on_model_changed(self, model_name):
        """Handle model change."""
        self.gemini_client.update_model(model_name)
        self.signals.status_update.emit(f"✅ Model: {model_name}")

    def update_system_prompt(self):
        """Update system prompt."""
        instructions = self.system_prompt_input.toPlainText().strip()
        self.gemini_client.update_instructions(instructions)
        self.signals.status_update.emit("✅ Instructions updated")

    def toggle_transcription(self):
        """Toggle transcription state."""
        if not self.audio_transcriber.is_transcribing:
            api_key = self.azure_key_input.text() or Config.SPEECH_KEY
            region = self.azure_region_input.text() or Config.SPEECH_REGION
            
            if self.audio_transcriber.start(api_key, region):
                self.transcribe_button.setText("⏹ Stop Transcription")
                self.transcribe_button.setProperty("class", "transcribe-btn-active")
                self.transcribe_button.style().unpolish(self.transcribe_button)
                self.transcribe_button.style().polish(self.transcribe_button)
        else:
            self.audio_transcriber.stop()
            self.transcribe_button.setText("🎤 Start Transcription")
            self.transcribe_button.setProperty("class", "transcribe-btn")
            self.transcribe_button.style().unpolish(self.transcribe_button)
            self.transcribe_button.style().polish(self.transcribe_button)
            self.signals.status_update.emit("Status: Stopped | Press Alt+X for screenshot")

    def update_transcription(self, text):
        """Handle transcribed text."""
        if text.startswith("✅"):
            clean_text = text.replace("✅", "").strip()
            if clean_text:
                self.send_to_gemini(clean_text)

    def send_to_gemini(self, text):
        """Send text to Gemini."""
        if not self.gemini_client.chat:
            self.signals.status_update.emit("❌ Error: Gemini API not configured. Check your API key in settings.")
            return
        
        def gemini_worker():
            try:
                self.signals.add_user_message.emit(text)
                self.signals.add_assistant_message_start.emit()
                
                response = self.gemini_client.send_message_stream(text)
                
                if response is None:
                    self.signals.status_update.emit("❌ No response from Gemini. Check your API key and internet connection.")
                    return
                
                for chunk in response:
                    if hasattr(chunk, 'text') and chunk.text:
                        self.signals.add_assistant_chunk.emit(chunk.text)
                
                if self.chunk_buffer:
                    QTimer.singleShot(0, self._render_assistant_message_safe)
                
            except Exception as e:
                error_msg = str(e)
                if "not configured" in error_msg.lower():
                    self.signals.status_update.emit(f"❌ {error_msg}")
                elif "failed" in error_msg.lower():
                    self.signals.status_update.emit(f"❌ Gemini Error: {error_msg}")
                else:
                    self.signals.status_update.emit(f"❌ Error: {error_msg}")
        
        threading.Thread(target=gemini_worker, daemon=True).start()

    def setup_hotkey(self):
        """Setup global hotkey."""
        def on_screenshot_hotkey():
            self.signals.screenshot_signal.emit()
        
        self.hotkey_listener = keyboard.GlobalHotKeys({
            '<alt>+x': on_screenshot_hotkey
        })
        self.hotkey_listener.start()

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
            self.send_screenshot_to_gemini(self.current_screenshot_bytes)
            self.signals.status_update.emit("Screenshot captured and sent to AI")
        except Exception as e:
            self.signals.status_update.emit(f"Screenshot error: {str(e)}")
        finally:
            if was_visible:
                self.signals.restore_window_signal.emit()

    def send_screenshot_to_gemini(self, image_bytes):
        """Send screenshot to Gemini."""
        if not self.gemini_client.chat:
            self.signals.status_update.emit("❌ Error: Gemini API not configured. Check your API key in settings.")
            return
        
        def gemini_screenshot_worker():
            try:
                self.signals.add_assistant_message_start.emit()
                response = self.gemini_client.send_screenshot_stream(image_bytes)
                
                if response is None:
                    self.signals.status_update.emit("❌ No response from Gemini. Check your API key and internet connection.")
                    return
                
                for chunk in response:
                    if hasattr(chunk, 'text') and chunk.text:
                        self.signals.add_assistant_chunk.emit(chunk.text)
                
                if self.chunk_buffer:
                    QTimer.singleShot(0, self._render_assistant_message_safe)
                
            except Exception as e:
                error_msg = str(e)
                if "not configured" in error_msg.lower():
                    self.signals.status_update.emit(f"❌ {error_msg}")
                elif "failed" in error_msg.lower():
                    self.signals.status_update.emit(f"❌ Gemini Error: {error_msg}")
                else:
                    self.signals.status_update.emit(f"❌ Screenshot Error: {error_msg}")
        
        threading.Thread(target=gemini_screenshot_worker, daemon=True).start()

    def restore_window(self):
        """Restore window to front."""
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
                    color: #f57173;
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
                    <div style="color: #f57173;"><span id="asst_content_placeholder"></span></div>
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
                    color: #f57173;
                    padding: 14px 18px;
                    border-radius: 12px;
                    word-wrap: break-word;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
                    font-size: 14px;
                    line-height: 1.6;
                    border: 1px solid #5d1619;
                ">
                    <div style="margin-bottom: 6px; font-weight: 600; color: #ff9597; font-size: 12px;">🤖 AI Assistant</div>
                    <div style="color: #f57173;">{html_content}</div>
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
        
        event.accept()

    def show_startup_dialog(self):
        """Show dialog to get Resume context at startup."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Startup Configuration")
        dialog.setMinimumWidth(450)
        
        layout = QVBoxLayout(dialog)
        
        # Header
        header = QLabel("👋 Welcome! Please configure your AI Assistant.")
        header.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Resume Context
        layout.addWidget(QLabel("📝 Resume / Context (Optional):"))
        layout.addWidget(QLabel("Paste your resume or specific instructions here to help the AI understand your background."))
        
        resume_input = QTextEdit()
        resume_input.setPlaceholderText("Paste resume text here...")
        resume_input.setMinimumHeight(120)
        layout.addWidget(resume_input)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        # Style the dialog
        dialog.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #ffffff; }
            QLabel { color: #ffffff; }
            QLineEdit, QTextEdit { 
                background-color: #2d2d2d; 
                color: #ffffff; 
                border: 1px solid #3d3d3d;
                padding: 5px;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #0b5ed7; }
        """)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            resume_text = resume_input.toPlainText().strip()
            
            # Update System Prompt with Resume
            if resume_text:
                current_prompt = self.system_prompt_input.toPlainText()
                new_prompt = f"{current_prompt}\n\n### User Resume / Context ###\n{resume_text}".strip()
                self.system_prompt_input.setText(new_prompt)
                self.gemini_client.update_instructions(new_prompt)
                self.signals.status_update.emit("✅ Resume context saved!")
            else:
                self.signals.status_update.emit("✅ Ready!")

