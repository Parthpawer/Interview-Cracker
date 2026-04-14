import os
import time
from google import genai
from google.genai import types
from src.config import Config


class GeminiClient:
    """Client for interacting with Google Gemini API with dynamic multi-key handling.
    
    Key Strategy:
    - Uses ONLY one key at a time
    - Continues using the same key until it hits quota/rate limit
    - On quota/rate error: switches to the next key
    - Tries maximum 2 keys per request (avoids long delays)
    - Maintains persistent current_key_index across requests
    """

    MAX_KEYS_PER_REQUEST = 2  # Try at most 2 keys per request to avoid delay

    FIXED_SYSTEM_PROMPT = (
        "You are a helpful AI assistant integrated into a desktop application. "
        "You help users with transcribed audio, screenshots, and general queries. "
        "Always provide concise, accurate, and helpful responses."
    )

    def __init__(self):
        self.api_keys = Config.GEMINI_API_KEYS
        self.current_key_index = 0
        self.client = None
        self.chat = None
        self.current_model = Config.GEMINI_MODEL
        self.additional_instructions = Config.SYSTEM_PROMPT
        self._initialize_client()

    # ==================== KEY MANAGEMENT ====================

    def _get_current_key(self):
        """Return the currently active API key."""
        if not self.api_keys:
            return None
        return self.api_keys[self.current_key_index]

    def _switch_key(self):
        """Move to the next API key in the list."""
        if not self.api_keys or len(self.api_keys) <= 1:
            return False
        old_idx = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        print(f"🔄 Switching API key: #{old_idx + 1} → #{self.current_key_index + 1}")
        return True

    def _is_quota_error(self, error_str):
        """Check if the error is a quota or rate limit error."""
        return any(keyword in error_str for keyword in ["429", "quota", "exhausted", "rate limit"])

    # ==================== CLIENT INITIALIZATION ====================

    def _initialize_client(self):
        """Initialize the Gemini client with the current API key."""
        key = self._get_current_key()
        if not key:
            print("⚠️ No Gemini API keys configured")
            return False

        try:
            self.client = genai.Client(api_key=key)
            self.chat = None  # Reset chat so it gets recreated with new client
            print(f"✅ Gemini client initialized with key #{self.current_key_index + 1}")
            return True
        except Exception as e:
            print(f"❌ Gemini init error (key #{self.current_key_index + 1}): {e}")
            return False

    def _ensure_chat(self):
        """Create a chat session if one doesn't exist."""
        if self.chat:
            return True

        if not self.client:
            if not self._initialize_client():
                return False

        try:
            full_instruction = self.get_full_system_instruction()
            self.chat = self.client.chats.create(
                model=self.current_model,
                config={"system_instruction": full_instruction}
            )
            return True
        except Exception as e:
            print(f"❌ Error creating chat: {e}")
            return False

    # ==================== CONFIGURATION ====================

    def get_full_system_instruction(self):
        """Combine fixed system prompt with additional instructions."""
        if self.additional_instructions.strip():
            return f"{self.FIXED_SYSTEM_PROMPT}\n\nAdditional Instructions:\n{self.additional_instructions}"
        return self.FIXED_SYSTEM_PROMPT

    def update_model(self, model_name):
        """Update the model and recreate chat."""
        self.current_model = model_name
        self.chat = None
        return self._ensure_chat()

    def update_instructions(self, instructions):
        """Update system instructions and recreate chat."""
        self.additional_instructions = instructions
        self.chat = None
        return self._ensure_chat()

    def get_status(self):
        """Get current client status."""
        return {
            'model': self.current_model,
            'api_keys_available': len(self.api_keys),
            'current_key_index': self.current_key_index + 1,
            'total_keys': len(self.api_keys)
        }

    # ==================== API CALLS ====================

    def send_message_stream(self, text, model_name: str | None = None):
        """Send text message using dynamic multi-key handling.
        
        Logic:
        1. Use current key to call Gemini
        2. If quota/rate error → switch_key() → retry with next key
        3. Maximum 2 keys tried per request
        4. Other errors → fail immediately (no retry)
        """
        # Temporarily use requested model if specified
        original_model = self.current_model
        if model_name:
            self.current_model = model_name
            self.chat = None

        try:
            for attempt in range(self.MAX_KEYS_PER_REQUEST):
                # Ensure client and chat are ready
                if not self._ensure_chat():
                    raise Exception("⚠️ Gemini API not configured. Please add API keys in Settings.")

                try:
                    response = self.chat.send_message_stream(text)
                    for chunk in response:
                        yield chunk
                    # Success — keep using this key for future requests
                    return

                except Exception as e:
                    error_str = str(e).lower()
                    print(f"❌ API Error (key #{self.current_key_index + 1}): {error_str[:120]}")

                    if self._is_quota_error(error_str):
                        # Switch to next key and retry
                        if attempt < self.MAX_KEYS_PER_REQUEST - 1 and self._switch_key():
                            self.chat = None
                            self._initialize_client()
                            print(f"🔄 Retrying with key #{self.current_key_index + 1}...")
                            continue
                        else:
                            raise Exception("⚠️ API quota exceeded. Please try again in a few minutes.")
                    else:
                        # Non-quota error → fail immediately
                        raise Exception(f"⚠️ {str(e)}")

            # Should not reach here, but just in case
            raise Exception("⚠️ All attempted API keys exhausted. Try again later.")

        finally:
            # Restore original model if we temporarily changed it
            if model_name:
                self.current_model = original_model
                self.chat = None

    def send_screenshot_stream(self, image_bytes, prompt="What do you see in this screenshot? Please describe it and provide any relevant insights or help."):
        """Send screenshot using dynamic multi-key handling.
        
        Same logic as send_message_stream:
        1. Use current key
        2. Switch on quota/rate error
        3. Max 2 keys per request
        """
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type='image/png'
        )

        for attempt in range(self.MAX_KEYS_PER_REQUEST):
            # Ensure client and chat are ready
            if not self._ensure_chat():
                raise Exception("⚠️ Gemini API not configured. Please add API keys in Settings.")

            try:
                response = self.chat.send_message_stream([image_part, prompt])
                for chunk in response:
                    yield chunk
                # Success — keep using this key
                return

            except Exception as e:
                error_str = str(e).lower()
                print(f"❌ Screenshot Error (key #{self.current_key_index + 1}): {error_str[:120]}")

                if self._is_quota_error(error_str):
                    if attempt < self.MAX_KEYS_PER_REQUEST - 1 and self._switch_key():
                        self.chat = None
                        self._initialize_client()
                        print(f"🔄 Retrying screenshot with key #{self.current_key_index + 1}...")
                        continue
                    else:
                        raise Exception("⚠️ API quota exceeded. Please try again in a few minutes.")
                else:
                    raise Exception(f"⚠️ {str(e)}")

        raise Exception("⚠️ Unable to process screenshot. Try again later.")
