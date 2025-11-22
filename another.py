import sys
import ctypes
import os
import threading
import time
import io
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, 
    QPushButton, QTextEdit, QScrollArea, QComboBox, QSizeGrip, QLineEdit,
    QTabWidget, QFrame, QListView
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QPoint, QEvent, QRect, QTimer
from PyQt6.QtGui import QTextCursor, QMouseEvent, QCursor

from dotenv import load_dotenv
load_dotenv()

import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech.audio import AudioStreamFormat, PushAudioInputStream

import pyaudiowpatch as pyaudio

import numpy as np
from scipy import signal

from PIL import ImageGrab
from pynput import keyboard

from google import genai
from google.genai import types

import markdown


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


class CustomComboBox(QComboBox):
    """Custom QComboBox that hides popup from screen capture"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chunk_buffer = []
        self.last_ui_update = time.time()
        self.update_timer = None
        self.screen_share_hidden = False
        self.user32 = ctypes.windll.user32
        self.WDA_EXCLUDEFROMCAPTURE = 0x11
        self.WDA_NONE = 0x00
        
    def showPopup(self):
        """Override to apply screen capture exclusion before showing popup"""
        super().showPopup()
        if self.screen_share_hidden:
            popup = self.view().window()
            if popup:
                hwnd = int(popup.winId())
                self.user32.SetWindowDisplayAffinity(hwnd, self.WDA_EXCLUDEFROMCAPTURE)
    
    def set_screen_share_hidden(self, hidden):
        """Set whether popup should be hidden from screen sharing"""
        self.screen_share_hidden = hidden


class VisibilityApp(QWidget):
    def __init__(self):
        super().__init__()

        self.chunk_buffer = []
        self.last_ui_update = time.time()
        self.update_timer = None
        
        self.FIXED_SYSTEM_PROMPT = """You are a helpful AI assistant integrated into a desktop application. You help users with transcribed audio, screenshots, and general queries. Always provide concise, accurate, and helpful responses."""

        self.setWindowTitle("AI Assistant with Live Transcription")
        self.resize(1200, 700)
        self.setMinimumSize(400, 300)
        
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
        
        # Enhanced styling with border for resize indication
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
            QLineEdit {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
            }
            QTextEdit {
                background-color: #252525;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 10px;
            }
            QComboBox {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 8px;
            }
            QComboBox:hover {
                border: 1px solid #4d4d4d;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #e0e0e0;
                selection-background-color: #007acc;
                border: 1px solid #3d3d3d;
            }
            QCheckBox {
                color: #e0e0e0;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 1px solid #3d3d3d;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #007acc;
                border: 1px solid #007acc;
            }
            QTabWidget::pane {
                border: 1px solid #3d3d3d;
                background-color: #1e1e1e;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #a0a0a0;
                border: 1px solid #3d3d3d;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border-bottom: 1px solid #1e1e1e;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3d3d3d;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #4d4d4d;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5d5d5d;
            }
        """)

        # Main container with border for resize indication
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
            }
        """)
        
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
        
        # Title bar with window controls
        title_bar_widget = QWidget()
        title_bar_widget.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-radius: 5px;
                margin-bottom: 10px;
            }
        """)
        title_bar_layout = QHBoxLayout(title_bar_widget)
        title_bar_layout.setContentsMargins(12, 8, 12, 8)
        
        title_bar = QLabel("🤖 AI Assistant")
        title_bar.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #e0e0e0;
                font-size: 16px;
                font-weight: bold;
                border: none;
            }
        """)
        
        # Window control buttons
        minimize_btn = QPushButton("−")
        minimize_btn.setFixedSize(30, 30)
        minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 15px;
                font-size: 18px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #007acc;
            }
        """)
        minimize_btn.clicked.connect(self.showMinimized)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 15px;
                font-size: 20px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
        """)
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
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #252525;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
            }
        """)
        
        control_bar = QWidget()
        control_bar.setStyleSheet("background-color: #252525; border-radius: 5px; padding: 10px;")
        control_layout = QHBoxLayout(control_bar)
        
        self.transcribe_button = QPushButton("🎤 Start Transcription")
        self.transcribe_button.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #0098ff;
            }
        """)
        
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
        settings_container.setStyleSheet("background-color: #252525; border-left: 1px solid #3d3d3d;")
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        
        settings_title = QLabel("⚙️ Settings")
        settings_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px; color: #e0e0e0;")
        
        settings_tabs = QTabWidget()
        
        # Tab 1: API Keys
        api_tab = QWidget()
        api_layout = QVBoxLayout(api_tab)
        api_layout.setSpacing(10)
        
        api_layout.addWidget(QLabel("Azure Speech API Key:"))
        self.azure_key_input = QLineEdit()
        self.azure_key_input.setPlaceholderText("Enter Azure API key")
        self.azure_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.azure_key_input.setText(os.getenv('SPEECH_KEY', ''))
        api_layout.addWidget(self.azure_key_input)
        
        api_layout.addWidget(QLabel("Azure Region:"))
        self.azure_region_input = QLineEdit()
        self.azure_region_input.setPlaceholderText("e.g., eastus")
        self.azure_region_input.setText(os.getenv('SPEECH_REGION', ''))
        api_layout.addWidget(self.azure_region_input)
        
        api_layout.addWidget(QLabel("Gemini API Key:"))
        self.gemini_key_input = QLineEdit()
        self.gemini_key_input.setPlaceholderText("Enter Gemini API key")
        self.gemini_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key_input.setText(os.getenv('GEMINI_API_KEY', '') or os.getenv('GOOGLE_API_KEY', ''))
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
            "gemini-2.0-flash-exp",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b"
        ])
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

        self.hwnd = None
        self.user32 = ctypes.windll.user32
        self.WDA_NONE = 0x00
        self.WDA_EXCLUDEFROMCAPTURE = 0x11

        self.is_transcribing = False
        self.transcription_thread = None
        self.audio_stream = None
        self.speech_recognizer = None
        
        self.additional_instructions = ""
        self.current_model = "gemini-2.0-flash-exp"
        try:
            gemini_api_key = self.gemini_key_input.text() or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
            if gemini_api_key:
                os.environ['GOOGLE_API_KEY'] = gemini_api_key
                self.gemini_client = genai.Client()
                self.gemini_chat = self.create_gemini_chat()
            else:
                self.gemini_client = None
                self.gemini_chat = None
        except Exception as e:
            self.gemini_client = None
            self.gemini_chat = None
            print(f"Gemini initialization error: {e}")
        
        self.current_assistant_message = ""
        self.current_screenshot_bytes = None
        
        self.signals = TranscriptionSignals()
        self.signals.transcription_update.connect(self.update_transcription)
        self.signals.status_update.connect(self.update_status)
        self.signals.screenshot_signal.connect(self.take_screenshot_safe)
        self.signals.restore_window_signal.connect(self.restore_window)
        self.signals.add_user_message.connect(self.add_user_message_to_chat)
        self.signals.add_screenshot_message.connect(self.add_screenshot_message_to_chat)
        self.signals.add_assistant_message_start.connect(self.start_assistant_message)
        self.signals.add_assistant_chunk.connect(self.add_assistant_chunk)

        self.setup_hotkey()
        self.showEvent = self._on_show

    def save_api_keys(self):
        """Save API keys permanently to .env file and reinitialize services"""
        azure_key = self.azure_key_input.text().strip()
        azure_region = self.azure_region_input.text().strip()
        gemini_key = self.gemini_key_input.text().strip()
        
        # Save to memory (for current session)
        if azure_key:
            os.environ['SPEECH_KEY'] = azure_key
        if azure_region:
            os.environ['SPEECH_REGION'] = azure_region
        if gemini_key:
            os.environ['GOOGLE_API_KEY'] = gemini_key
            os.environ['GEMINI_API_KEY'] = gemini_key
        
        # Save to .env file for persistence across app restarts
        try:
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
            with open(env_path, 'w') as f:
                if azure_key:
                    f.write(f'SPEECH_KEY={azure_key}\n')
                if azure_region:
                    f.write(f'SPEECH_REGION={azure_region}\n')
                if gemini_key:
                    f.write(f'GEMINI_API_KEY={gemini_key}\n')
            
            # Reinitialize Gemini client if key provided
            if gemini_key:
                try:
                    self.gemini_client = genai.Client()
                    self.gemini_chat = self.create_gemini_chat()
                    self.signals.status_update.emit("✅ API keys saved permanently!")
                except Exception as e:
                    self.signals.status_update.emit(f"⚠️ Keys saved but Gemini error: {str(e)}")
            else:
                self.signals.status_update.emit("✅ API keys saved permanently!")
                
        except Exception as e:
            # Fallback: keys still work in memory for current session
            self.signals.status_update.emit(f"⚠️ Saved to memory only. File error: {str(e)}")
            
            # Still try to initialize Gemini
            if gemini_key:
                try:
                    self.gemini_client = genai.Client()
                    self.gemini_chat = self.create_gemini_chat()
                except Exception as e:
                    self.signals.status_update.emit(f"Error initializing Gemini: {str(e)}")

    def title_mouse_press(self, event: QMouseEvent):
        """Handle mouse press on title bar for dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def title_mouse_move(self, event: QMouseEvent):
        """Handle mouse move for window dragging"""
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def title_mouse_release(self, event: QMouseEvent):
        """Handle mouse release to stop dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for window resizing"""
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
        """Handle mouse move for cursor updates and resizing"""
        if self.resizing and self.resize_edge:
            self.resize_window(event.globalPosition().toPoint())
            event.accept()
        else:
            edge = self.get_resize_edge(event.pos())
            self.update_cursor_shape(edge)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to stop resizing"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.resizing = False
            self.resize_edge = None
            self.resize_start_pos = None
            self.resize_start_geo = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        super().mouseReleaseEvent(event)

    def get_resize_edge(self, pos):
        """Detect which edge/corner is being hovered for resizing"""
        rect = self.rect()
        bw = self.border_width
        
        on_left = pos.x() <= bw
        on_right = pos.x() >= rect.width() - bw
        on_top = pos.y() <= bw
        on_bottom = pos.y() >= rect.height() - bw
        
        if on_top and on_left:
            return 'top-left'
        elif on_top and on_right:
            return 'top-right'
        elif on_bottom and on_left:
            return 'bottom-left'
        elif on_bottom and on_right:
            return 'bottom-right'
        elif on_left:
            return 'left'
        elif on_right:
            return 'right'
        elif on_top:
            return 'top'
        elif on_bottom:
            return 'bottom'
        return None

    def update_cursor_shape(self, edge):
        """Update cursor based on resize edge"""
        if edge == 'top' or edge == 'bottom':
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edge == 'left' or edge == 'right':
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edge == 'top-left' or edge == 'bottom-right':
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edge == 'top-right' or edge == 'bottom-left':
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def resize_window(self, global_pos):
        """Handle window resizing based on drag position"""
        if not self.resize_start_geo or not self.resize_start_pos:
            return
        
        delta = global_pos - self.resize_start_pos
        geo = QRect(self.resize_start_geo)
        
        if 'left' in self.resize_edge:
            new_left = geo.left() + delta.x()
            new_width = geo.width() - delta.x()
            if new_width >= self.minimumWidth():
                geo.setLeft(new_left)
        
        if 'right' in self.resize_edge:
            new_width = geo.width() + delta.x()
            if new_width >= self.minimumWidth():
                geo.setRight(geo.right() + delta.x())
        
        if 'top' in self.resize_edge:
            new_top = geo.top() + delta.y()
            new_height = geo.height() - delta.y()
            if new_height >= self.minimumHeight():
                geo.setTop(new_top)
        
        if 'bottom' in self.resize_edge:
            new_height = geo.height() + delta.y()
            if new_height >= self.minimumHeight():
                geo.setBottom(geo.bottom() + delta.y())
        
        if geo.width() >= self.minimumWidth() and geo.height() >= self.minimumHeight():
            self.setGeometry(geo)

    def get_full_system_instruction(self):
        """Combine fixed system prompt with additional instructions"""
        if self.additional_instructions.strip():
            return f"{self.FIXED_SYSTEM_PROMPT}\n\nAdditional Instructions:\n{self.additional_instructions}"
        else:
            return self.FIXED_SYSTEM_PROMPT

    def create_gemini_chat(self):
        """Create a new Gemini chat instance with combined system instruction and model"""
        if not self.gemini_client:
            return None
        
        try:
            full_instruction = self.get_full_system_instruction()
            return self.gemini_client.chats.create(
                model=self.current_model,
                config={
                    "system_instruction": full_instruction
                }
            )
        except Exception as e:
            print(f"Error creating Gemini chat: {e}")
            return None

    def on_model_changed(self, model_name):
        """Handle model selection change"""
        self.current_model = model_name
        
        if self.gemini_client:
            self.gemini_chat = self.create_gemini_chat()
            self.signals.status_update.emit(f"✅ Model: {model_name}")

    def update_system_prompt(self):
        """Update the additional instructions and recreate the Gemini chat"""
        new_instructions = self.system_prompt_input.toPlainText().strip()
        
        self.additional_instructions = new_instructions
        
        if self.gemini_client:
            self.gemini_chat = self.create_gemini_chat()
            
            if new_instructions:
                self.signals.status_update.emit("✅ Instructions updated")
            else:
                self.signals.status_update.emit("✅ Base prompt only")
            
            self.scroll_to_bottom()
        else:
            self.signals.status_update.emit("Error: Gemini not initialized")

    def setup_hotkey(self):
        """Setup global hotkey for screenshot"""
        def on_screenshot_hotkey():
            self.signals.screenshot_signal.emit()
        
        self.hotkey_listener = keyboard.GlobalHotKeys({
            '<alt>+x': on_screenshot_hotkey
        })
        self.hotkey_listener.start()

    def take_screenshot_safe(self):
        """Thread-safe screenshot handler"""
        was_visible = self.isVisible()
        
        if was_visible:
            self.hide()
            time.sleep(0.3)
        
        threading.Thread(target=self._take_screenshot_thread, args=(was_visible,), daemon=True).start()

    def _take_screenshot_thread(self, was_visible):
        """Take screenshot in separate thread and send to Gemini"""
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

    def restore_window(self):
        """Restore window to front after screenshot"""
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

    def _on_show(self, event):
        """Called when the window first appears; captures HWND handle"""
        self.hwnd = self.user32.FindWindowW(None, self.windowTitle())

    def toggle_taskbar(self):
        """Hide or show the app in Windows taskbar"""
        if self.taskbar_toggle.isChecked():
            self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self.show()
        else:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self.show()

    def toggle_screenshare(self):
        """Exclude or include window from screen capture (Teams, Zoom, etc.)"""
        if not self.hwnd:
            self.hwnd = self.user32.FindWindowW(None, self.windowTitle())

        if self.hwnd:
            if self.screenshare_toggle.isChecked():
                self.user32.SetWindowDisplayAffinity(self.hwnd, self.WDA_EXCLUDEFROMCAPTURE)
                self.model_selector.set_screen_share_hidden(True)
            else:
                self.user32.SetWindowDisplayAffinity(self.hwnd, self.WDA_NONE)
                self.model_selector.set_screen_share_hidden(False)

    def markdown_to_html(self, text):
        """Convert markdown text to HTML with custom theme colors"""
        html = markdown.markdown(text, extensions=['extra', 'nl2br', 'sane_lists', 'fenced_code'])
        html = html.replace('<code>', '<code style="background-color: #2d0708; color: #ffb3b5; padding: 2px 6px; border-radius: 4px; font-family: Consolas, monospace; font-size: 0.9em; border: 1px solid #5d1619;">')
        html = html.replace('<pre>', '<pre style="background-color: #2d0708; color: #f57173; padding: 16px; border-radius: 8px; overflow-x: auto; border: 1px solid #5d1619; margin: 10px 0;">')
        html = html.replace('<pre><code>', '<pre><code style="background-color: transparent; color: #f57173; padding: 0;">')
        return html

    def add_user_message_to_chat(self, text):
        """Add user message (transcribed text) to chat display"""
        print(f"[add_user_message_to_chat] Adding user message: {text[:50]}...")
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
        print("[add_user_message_to_chat] User message added")

    def add_screenshot_message_to_chat(self):
        """Add screenshot message to chat display"""
        print("[add_screenshot_message_to_chat] Adding screenshot message")
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
        print("[add_screenshot_message_to_chat] Screenshot message added")

    def start_assistant_message(self):
        """Start a new assistant message"""
        print("[start_assistant_message] Starting new assistant message")
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
        print("[start_assistant_message] Assistant message placeholder added")

    def add_assistant_chunk(self, chunk):
        """Buffer chunks and update UI periodically to reduce flicker - THREAD SAFE"""
        self.chunk_buffer.append(chunk)
        current_time = time.time()
        
        # Check if we should update, but DON'T call render directly from signal handler
        # The signal connection ensures this runs in the main thread
        if current_time - self.last_ui_update > 0.15 or len(self.chunk_buffer) > 8:
            # Safely update in main GUI thread
            self._render_assistant_message_safe()

    def _render_assistant_message_safe(self):
        """Thread-safe wrapper for rendering assistant message"""
        # This ensures rendering happens in the main GUI thread
        if not self.chunk_buffer:
            return
        self._render_assistant_message()

    def _render_assistant_message(self):
        """Actually render the accumulated assistant message - MUST run in main thread"""
        if not self.chunk_buffer:
            return
        
        self.current_assistant_message += ''.join(self.chunk_buffer)
        self.chunk_buffer = []
        self.last_ui_update = time.time()
        
        html_content = self.markdown_to_html(self.current_assistant_message)
        
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
        """Scroll chat to bottom"""
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def send_to_gemini(self, text):
        """Send transcribed text to Gemini and stream response"""
        if not self.gemini_chat:
            self.signals.status_update.emit("Error: Gemini API not configured")
            return
        
        def gemini_worker():
            try:
                self.signals.add_user_message.emit(text)
                self.signals.add_assistant_message_start.emit()
                
                response = self.gemini_chat.send_message_stream(text)
                
                for chunk in response:
                    if hasattr(chunk, 'text') and chunk.text:
                        self.signals.add_assistant_chunk.emit(chunk.text)
                
                # Flush remaining chunks in main thread using QTimer
                if self.chunk_buffer:
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(0, self._render_assistant_message_safe)
                
            except Exception as e:
                self.signals.status_update.emit(f"Gemini error: {str(e)}")
        
        threading.Thread(target=gemini_worker, daemon=True).start()

    def send_screenshot_to_gemini(self, image_bytes):
        """Send screenshot to Gemini and stream response"""
        if not self.gemini_chat:
            self.signals.status_update.emit("Error: Gemini API not configured")
            return
        
        def gemini_screenshot_worker():
            try:
                self.signals.add_assistant_message_start.emit()
                
                image_part = types.Part.from_bytes(
                    data=image_bytes,
                    mime_type='image/png'
                )
                
                response = self.gemini_chat.send_message_stream([
                    image_part,
                    "What do you see in this screenshot? Please describe it and provide any relevant insights or help."
                ])
                
                for chunk in response:
                    if hasattr(chunk, 'text') and chunk.text:
                        self.signals.add_assistant_chunk.emit(chunk.text)
                
                # Flush remaining chunks in main thread using QTimer
                if self.chunk_buffer:
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(0, self._render_assistant_message_safe)
                
            except Exception as e:
                self.signals.status_update.emit(f"Gemini screenshot error: {str(e)}")
        
        threading.Thread(target=gemini_screenshot_worker, daemon=True).start()

    def toggle_transcription(self):
        """Start or stop live transcription"""
        if not self.is_transcribing:
            self.start_transcription()
        else:
            self.stop_transcription()

    def start_transcription(self):
        """Start capturing system audio and transcribing"""
        api_key = self.azure_key_input.text() or os.getenv('SPEECH_KEY')
        region = self.azure_region_input.text() or os.getenv('SPEECH_REGION')

        if not api_key or not region:
            self.signals.status_update.emit("Error: Set Azure API key and region in Settings")
            return

        self.is_transcribing = True
        self.transcribe_button.setText("⏹ Stop Transcription")
        self.transcribe_button.setStyleSheet("""
            QPushButton {
                background-color: #cc0000;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #ff0000;
            }
        """)
        self.signals.status_update.emit("Status: Starting transcription...")

        self.transcription_thread = threading.Thread(
            target=self._transcription_worker,
            args=(api_key, region),
            daemon=True
        )
        self.transcription_thread.start()

    def stop_transcription(self):
        """Stop transcription"""
        self.is_transcribing = False
        self.transcribe_button.setText("🎤 Start Transcription")
        self.transcribe_button.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #0098ff;
            }
        """)
        self.signals.status_update.emit("Status: Stopped | Press Alt+X for screenshot")

        if self.speech_recognizer:
            try:
                self.speech_recognizer.stop_continuous_recognition()
            except:
                pass

    def update_transcription(self, text):
        """Handle transcribed text - partial or final"""
        if text.startswith("✅"):
            clean_text = text.replace("✅", "").strip()
            if clean_text:
                self.send_to_gemini(clean_text)

    def resample_audio(self, audio_data, orig_rate, target_rate=16000):
        """Resample audio to target rate"""
        try:
            number_of_samples = round(len(audio_data) * float(target_rate) / orig_rate)
            resampled = signal.resample(audio_data, number_of_samples)
            return resampled.astype(np.int16)
        except:
            return audio_data

    def _transcription_worker(self, api_key, region):
        """Worker thread for audio capture and transcription"""
        p = None
        stream = None
        
        try:
            speech_config = speechsdk.SpeechConfig(subscription=api_key, region=region)
            speech_config.speech_recognition_language = "en-US"
            
            audio_format = AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1)
            self.audio_stream = PushAudioInputStream(stream_format=audio_format)
            audio_config = speechsdk.audio.AudioConfig(stream=self.audio_stream)
            
            self.speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            
            def recognized_cb(evt):
                if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    self.signals.transcription_update.emit(f"✅ {evt.result.text}")
            
            def canceled_cb(evt):
                error_msg = f"Recognition canceled: {evt.result.cancellation_details.reason}"
                if evt.result.cancellation_details.error_details:
                    error_msg += f" - {evt.result.cancellation_details.error_details}"
                self.signals.status_update.emit(f"Error: {error_msg}")
                self.is_transcribing = False
            
            self.speech_recognizer.recognized.connect(recognized_cb)
            self.speech_recognizer.canceled.connect(canceled_cb)
            
            self.speech_recognizer.start_continuous_recognition()
            
            p = pyaudio.PyAudio()
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            
            loopback_device = None
            if default_speakers.get("isLoopbackDevice"):
                loopback_device = default_speakers
            else:
                for loopback in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        loopback_device = loopback
                        break
            
            if not loopback_device:
                self.signals.status_update.emit("Error: No loopback device found")
                return
            
            device_channels = loopback_device["maxInputChannels"]
            device_rate = int(loopback_device["defaultSampleRate"])
            
            CHUNK = 1024
            stream = p.open(
                format=pyaudio.paInt16,
                channels=device_channels,
                rate=device_rate,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=loopback_device["index"]
            )
            
            self.signals.status_update.emit("Status: Recording and transcribing...")
            
            while self.is_transcribing:
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    
                    if device_channels == 2:
                        audio_data = audio_data.reshape(-1, 2).mean(axis=1).astype(np.int16)
                    
                    if device_rate != 16000:
                        audio_data = self.resample_audio(audio_data, device_rate, 16000)
                    
                    self.audio_stream.write(audio_data.tobytes())
                    
                except Exception as e:
                    pass
                
        except Exception as e:
            self.signals.status_update.emit(f"Error: {str(e)}")
            
        finally:
            try:
                if stream:
                    stream.stop_stream()
                    stream.close()
                if p:
                    p.terminate()
                if self.audio_stream:
                    self.audio_stream.close()
                if self.speech_recognizer:
                    self.speech_recognizer.stop_continuous_recognition()
            except:
                pass

    def update_status(self, status):
        """Update status label (thread-safe)"""
        self.status_label.setText(status)

    def closeEvent(self, event):
        """Cleanup on close"""
        if self.is_transcribing:
            self.stop_transcription()
        
        if hasattr(self, 'hotkey_listener'):
            self.hotkey_listener.stop()
        
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setOverrideCursor(QCursor(Qt.CursorShape.ArrowCursor))
    window = VisibilityApp()
    window.show()
    sys.exit(app.exec())