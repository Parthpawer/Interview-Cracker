import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration and environment variables."""
    
    # Azure Speech
    SPEECH_KEY = os.getenv('SPEECH_KEY', '3VWroc2VFa88CGPbbXze7USej1yNZaDZk4oHPCm06TvG88Y9cgZPJQQJ99BKACGhslBXJ3w3AAAYACOGkzgI')
    SPEECH_REGION = os.getenv('SPEECH_REGION', 'centralindia')
    
    # Google Gemini
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    
    # App Settings
    APP_TITLE = "AI Assistant with Live Transcription"
    DEFAULT_WIDTH = 1200
    DEFAULT_HEIGHT = 700
    MIN_WIDTH = 400
    MIN_HEIGHT = 300
    
    @staticmethod
    def save_env(speech_key=None, speech_region=None, gemini_key=None):
        """Save updated credentials to .env file."""
        env_path = os.path.join(os.getcwd(), '.env')
        
        # Update current session
        if speech_key:
            os.environ['SPEECH_KEY'] = speech_key
        if speech_region:
            os.environ['SPEECH_REGION'] = speech_region
        if gemini_key:
            os.environ['GOOGLE_API_KEY'] = gemini_key
            os.environ['GEMINI_API_KEY'] = gemini_key
            
        # Write to file
        try:
            lines = []
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()
            
            new_lines = []
            keys_updated = {'SPEECH_KEY': False, 'SPEECH_REGION': False, 'GEMINI_API_KEY': False}
            
            for line in lines:
                if line.startswith('SPEECH_KEY=') and speech_key:
                    new_lines.append(f'SPEECH_KEY={speech_key}\n')
                    keys_updated['SPEECH_KEY'] = True
                elif line.startswith('SPEECH_REGION=') and speech_region:
                    new_lines.append(f'SPEECH_REGION={speech_region}\n')
                    keys_updated['SPEECH_REGION'] = True
                elif line.startswith('GEMINI_API_KEY=') and gemini_key:
                    new_lines.append(f'GEMINI_API_KEY={gemini_key}\n')
                    keys_updated['GEMINI_API_KEY'] = True
                else:
                    new_lines.append(line)
            
            # Append new keys if not found
            if speech_key and not keys_updated['SPEECH_KEY']:
                new_lines.append(f'SPEECH_KEY={speech_key}\n')
            if speech_region and not keys_updated['SPEECH_REGION']:
                new_lines.append(f'SPEECH_REGION={speech_region}\n')
            if gemini_key and not keys_updated['GEMINI_API_KEY']:
                new_lines.append(f'GEMINI_API_KEY={gemini_key}\n')
                
            with open(env_path, 'w') as f:
                f.writelines(new_lines)
                
            return True, "✅ API keys saved permanently!"
        except Exception as e:
            return False, f"⚠️ Saved to memory only. File error: {str(e)}"
