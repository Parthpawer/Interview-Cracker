import os
from google import genai
from google.genai import types
from src.config import Config

class GeminiClient:
    """Client for interacting with Google Gemini API."""
    
    FIXED_SYSTEM_PROMPT = """You are a helpful AI assistant integrated into a desktop application. You help users with transcribed audio, screenshots, and general queries. Always provide concise, accurate, and helpful responses."""

    def __init__(self):
        self.client = None
        self.chat = None
        self.current_model = Config.GEMINI_MODEL
        self.additional_instructions = ""
        self.initialize()

    def initialize(self):
        """Initialize the Gemini client with API key."""
        # Prefer env var (dynamic) over Config (static)
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY') or Config.GEMINI_API_KEY
        if api_key:
            try:
                os.environ['GOOGLE_API_KEY'] = api_key
                self.client = genai.Client()
                self.create_chat()
                return True
            except Exception as e:
                print(f"Gemini initialization error: {e}")
                return False
        return False

    def get_full_system_instruction(self):
        """Combine fixed system prompt with additional instructions."""
        if self.additional_instructions.strip():
            return f"{self.FIXED_SYSTEM_PROMPT}\n\nAdditional Instructions:\n{self.additional_instructions}"
        else:
            return self.FIXED_SYSTEM_PROMPT

    def create_chat(self):
        """Create a new Gemini chat instance."""
        if not self.client:
            return None
        
        try:
            full_instruction = self.get_full_system_instruction()
            self.chat = self.client.chats.create(
                model=self.current_model,
                config={
                    "system_instruction": full_instruction
                }
            )
            return self.chat
        except Exception as e:
            print(f"Error creating Gemini chat: {e}")
            return None

    def update_model(self, model_name):
        """Update the model and recreate chat."""
        self.current_model = model_name
        return self.create_chat()

    def update_instructions(self, instructions):
        """Update system instructions and recreate chat."""
        self.additional_instructions = instructions
        return self.create_chat()

    def send_message_stream(self, text):
        """Send text message and yield stream response."""
        if not self.chat:
            raise Exception("Gemini API not configured")
            
        return self.chat.send_message_stream(text)

    def send_screenshot_stream(self, image_bytes, prompt="What do you see in this screenshot? Please describe it and provide any relevant insights or help."):
        """Send screenshot and yield stream response."""
        if not self.chat:
            raise Exception("Gemini API not configured")
            
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type='image/png'
        )
        
        return self.chat.send_message_stream([
            image_part,
            prompt
        ])
