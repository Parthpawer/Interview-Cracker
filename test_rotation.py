import sys
import os
from src.config import Config
from src.core.gemini import GeminiClient
import traceback

def test_gemini():
    print("Testing Gemini configuration...")
    print(f"Loaded {len(Config.GEMINI_API_KEYS)} keys from Config: {Config.GEMINI_API_KEYS}")
    
    client = GeminiClient()
    print(f"Initialized GeminiClient. Current key index: {client.current_key_idx}")
    
    # Test a simple prompt
    test_prompt = "Say hello!"
    print(f"Sending prompt: '{test_prompt}'")
    
    try:
        response_stream = client.send_message_stream(test_prompt)
        response_text = ""
        for chunk in response_stream:
            if hasattr(chunk, 'text') and chunk.text:
                response_text += chunk.text
        print("\n--- Response Received ---")
        print(response_text)
        print("-------------------------\n")
        print("✅ Gemini API is working successfully!")
    except Exception as e:
        print(f"[ERROR] Error during Gemini test: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_gemini()
