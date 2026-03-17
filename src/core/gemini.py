import os
from google import genai
from google.genai import types
from src.config import Config

class GeminiClient:
    """Client for interacting with Google Gemini API."""
    
    FIXED_SYSTEM_PROMPT = """You are a helpful AI assistant integrated into a desktop application. You help users with transcribed audio, screenshots, and general queries. Always provide concise, accurate, and helpful responses."""

    def __init__(self):
        self.api_keys = Config.GEMINI_API_KEYS
        self.current_key_idx = 0
        self.client = None
        self.chat = None
        self.current_model = Config.GEMINI_MODEL
        self.additional_instructions = Config.SYSTEM_PROMPT
        self.initialize()

    def initialize(self):
        """Initialize the Gemini client with current API key."""
        if not self.api_keys:
            return False
            
        current_api_key = self.api_keys[self.current_key_idx]
        try:
            self.client = genai.Client(api_key=current_api_key)
            self.create_chat()
            return True
        except Exception as e:
            print(f"Gemini initialization error with key idx {self.current_key_idx}: {e}")
            return False
            
    def _rotate_key(self):
        """Move to the next available API key and reinitialize."""
        if not self.api_keys or len(self.api_keys) <= 1:
            return False
            
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        print(f"Rate limited or quota exceeded. Rotating to Gemini API Key #{self.current_key_idx + 1}")
        return self.initialize()

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
        """Send text message with fallback retry on rate limits."""
        for attempt in range(len(self.api_keys) if self.api_keys else 1):
            if not self.chat:
                if not self.initialize():
                    raise Exception("Gemini API not configured or keys exhausted")

            try:
                response = self.chat.send_message_stream(text)
                for chunk in response:
                    yield chunk
                return
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "quota" in error_str or "exhausted" in error_str:
                    rotated = self._rotate_key()
                    if not rotated:
                        raise e
                    continue # Retry with new key
                else:
                    raise e
                    
        raise Exception("All Gemini API keys exhausted or rate-limited.")

    def send_screenshot_stream(self, image_bytes, prompt="What do you see in this screenshot? Please describe it and provide any relevant insights or help."):
        """Send screenshot with fallback retry on rate limits."""
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type='image/png'
        )
        
        for attempt in range(len(self.api_keys) if self.api_keys else 1):
            if not self.chat:
                if not self.initialize():
                    raise Exception("Gemini API not configured or keys exhausted")
                    
            try:
                response = self.chat.send_message_stream([
                    image_part,
                    prompt
                ])
                for chunk in response:
                    yield chunk
                return
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "quota" in error_str or "exhausted" in error_str:
                    rotated = self._rotate_key()
                    if not rotated:
                        raise e
                    continue # Retry with new key
                else:
                    raise e
                    
        raise Exception("All Gemini API keys exhausted or rate-limited.")
