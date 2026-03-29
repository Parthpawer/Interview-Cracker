import os
import sys
from dotenv import load_dotenv

# Compute absolute path for config based on context
if getattr(sys, 'frozen', False):
    # App is running as a PyInstaller executable
    base_path = os.path.dirname(sys.executable)
else:
    # App is running directly as Python script
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env_path = os.path.join(base_path, '.env')

# Load environment variables from exactly matching .env file
load_dotenv(env_path)

class Config:
    """Application configuration and environment variables."""
    
    # Azure Speech
    SPEECH_KEY_RAW = os.getenv('SPEECH_KEYS', '') or os.getenv('SPEECH_KEY', '')
    SPEECH_KEYS = [k.strip() for k in SPEECH_KEY_RAW.split(',')] if SPEECH_KEY_RAW else []
    SPEECH_REGION = os.getenv('SPEECH_REGION', '')
    
    # Google Gemini
    GEMINI_KEY_RAW = os.getenv('GEMINI_API_KEYS', '') or os.getenv('GEMINI_API_KEY', '') or os.getenv('GOOGLE_API_KEY', '')
    GEMINI_API_KEYS = [k.strip() for k in GEMINI_KEY_RAW.split(',')] if GEMINI_KEY_RAW else []
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')
    SYSTEM_PROMPT = os.getenv('SYSTEM_PROMPT', '').replace('\\n', '\n')
    
    # App Settings
    APP_TITLE = "AI Assistant with Live Transcription"
    DEFAULT_WIDTH = 1200
    DEFAULT_HEIGHT = 700
    MIN_WIDTH = 400
    MIN_HEIGHT = 300
    
    @staticmethod
    def save_env(speech_keys=None, speech_region=None, gemini_keys=None, gemini_model=None, system_prompt=None):
        """Save updated credentials and settings to precisely located .env file."""
        import os
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        env_path = os.path.join(base_dir, '.env')
        
        # Update current session
        if speech_keys:
            os.environ['SPEECH_KEYS'] = speech_keys
        if speech_region:
            os.environ['SPEECH_REGION'] = speech_region
        if gemini_keys:
            os.environ['GEMINI_API_KEYS'] = gemini_keys
        if gemini_model:
            os.environ['GEMINI_MODEL'] = gemini_model
        if system_prompt is not None:
            os.environ['SYSTEM_PROMPT'] = system_prompt.replace('\n', '\\n')
            
        # Write to file
        try:
            lines = []
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()
            
            new_lines = []
            keys_updated = {'SPEECH_KEY': False, 'SPEECH_REGION': False, 'GEMINI_API_KEY': False, 'GEMINI_MODEL': False, 'SYSTEM_PROMPT': False}
            
            for line in lines:
                if (line.startswith('SPEECH_KEY=') or line.startswith('SPEECH_KEYS=')) and speech_keys:
                    new_lines.append(f'SPEECH_KEYS={speech_keys}\n')
                    keys_updated['SPEECH_KEY'] = True
                elif line.startswith('SPEECH_REGION=') and speech_region:
                    new_lines.append(f'SPEECH_REGION={speech_region}\n')
                    keys_updated['SPEECH_REGION'] = True
                elif (line.startswith('GEMINI_API_KEY=') or line.startswith('GEMINI_API_KEYS=') or line.startswith('GOOGLE_API_KEY=')) and gemini_keys:
                    new_lines.append(f'GEMINI_API_KEYS={gemini_keys}\n')
                    keys_updated['GEMINI_API_KEY'] = True
                elif line.startswith('GEMINI_MODEL=') and gemini_model:
                    new_lines.append(f'GEMINI_MODEL={gemini_model}\n')
                    keys_updated['GEMINI_MODEL'] = True
                elif line.startswith('SYSTEM_PROMPT=') and system_prompt is not None:
                    prompt_escaped = system_prompt.replace('\n', '\\n')
                    new_lines.append(f'SYSTEM_PROMPT="{prompt_escaped}"\n')
                    keys_updated['SYSTEM_PROMPT'] = True
                else:
                    new_lines.append(line)
            
            # Append new keys if not found
            if speech_keys and not keys_updated['SPEECH_KEY']:
                new_lines.append(f'SPEECH_KEYS={speech_keys}\n')
            if speech_region and not keys_updated['SPEECH_REGION']:
                new_lines.append(f'SPEECH_REGION={speech_region}\n')
            if gemini_keys and not keys_updated['GEMINI_API_KEY']:
                new_lines.append(f'GEMINI_API_KEYS={gemini_keys}\n')
            if gemini_model and not keys_updated['GEMINI_MODEL']:
                new_lines.append(f'GEMINI_MODEL={gemini_model}\n')
            if system_prompt is not None and not keys_updated['SYSTEM_PROMPT']:
                prompt_escaped = system_prompt.replace('\n', '\\n')
                new_lines.append(f'SYSTEM_PROMPT="{prompt_escaped}"\n')
                
            with open(env_path, 'w') as f:
                f.writelines(new_lines)
                
            return True, "✅ Settings saved permanently!"
        except Exception as e:
            return False, f"⚠️ Saved to memory only. File error: {str(e)}"
