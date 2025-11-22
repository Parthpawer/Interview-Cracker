import os
import sys
import markdown
import numpy as np
from scipy import signal

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def markdown_to_html(text):
    """Convert markdown text to HTML with custom theme colors."""
    html = markdown.markdown(text, extensions=['extra', 'nl2br', 'sane_lists', 'fenced_code'])
    html = html.replace('<code>', '<code style="background-color: #2d0708; color: #ffb3b5; padding: 2px 6px; border-radius: 4px; font-family: Consolas, monospace; font-size: 0.9em; border: 1px solid #5d1619;">')
    html = html.replace('<pre>', '<pre style="background-color: #2d0708; color: #f57173; padding: 16px; border-radius: 8px; overflow-x: auto; border: 1px solid #5d1619; margin: 10px 0;">')
    html = html.replace('<pre><code>', '<pre><code style="background-color: transparent; color: #f57173; padding: 0;">')
    return html

def resample_audio(audio_data, orig_rate, target_rate=16000):
    """Resample audio to target rate."""
    try:
        number_of_samples = round(len(audio_data) * float(target_rate) / orig_rate)
        resampled = signal.resample(audio_data, number_of_samples)
        return resampled.astype(np.int16)
    except:
        return audio_data
