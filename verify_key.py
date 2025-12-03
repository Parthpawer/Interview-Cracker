import os
from dotenv import load_dotenv
import google.genai as genai

load_dotenv()

key = os.getenv('GEMINI_API_KEY')
print(f"Loaded Key: {key[:10]}...{key[-5:] if key else 'None'}")

if not key:
    print("No key found!")
    exit(1)

os.environ['GOOGLE_API_KEY'] = key
client = genai.Client(api_key=key)

try:
    print("Attempting to list models...")
    # Just try to list models or generate a simple content to test auth
    chat = client.chats.create(model='gemini-2.0-flash')
    response = chat.send_message("Hello")
    print("Success! Response:", response.text)
except Exception as e:
    print("Error:", e)
