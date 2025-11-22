# -*- mode: python ; coding: utf-8 -*-

import os

speech_sdk_path = os.path.join(os.getcwd(), "venv", "Lib", "site-packages", "azure", "cognitiveservices", "speech")

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        # All DLLs required by azure-cognitiveservices-speech
        (os.path.join(speech_sdk_path, "*.dll"), "azure/cognitiveservices/speech"),
    ],
    datas=[
        # All other files in the SDK folder
        (speech_sdk_path, "azure/cognitiveservices/speech"),
        # Include your .env file for API credentials
        ('.env', '.') if os.path.exists('.env') else None,
        # Include styles
        ('styles.qss', '.'),
    ],
    hiddenimports=[
        'azure.cognitiveservices.speech',
        'azure.cognitiveservices.speech.audio',
        'azure.cognitiveservices.speech.speech',
        'azure.cognitiveservices.speech.interop',
        'google.genai',
        'google.auth',
        'pynput',
        'pynput.keyboard',
        'pynput.keyboard._win32',
        'PIL.Image',
        'PIL.ImageGrab',
        'pyaudiowpatch',
        'scipy.signal',
        'numpy',
        'dotenv',
        'ctypes',
        'src',
        'src.core',
        'src.core.audio',
        'src.core.gemini',
        'src.ui',
        'src.ui.main_window',
        'src.ui.widgets',
        'src.utils',
        'src.utils.helpers',
        'src.config',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove None values from datas if .env doesn't exist
a.datas = [d for d in a.datas if d is not None]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AI-Assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Set icon path here if you have one
)
