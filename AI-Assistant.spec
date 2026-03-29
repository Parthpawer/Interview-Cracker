# -*- mode: python ; coding: utf-8 -*-
import os
import azure.cognitiveservices.speech

# -------------------------------------------------------------
# 1. Dependency Resolution
# -------------------------------------------------------------
# Dynamically get the path to the installed Azure SDK package
speech_sdk_path = os.path.dirname(azure.cognitiveservices.speech.__file__)

# -------------------------------------------------------------
# 2. Asset Bundling (Images, Styles, Envs)
# -------------------------------------------------------------
# Natively grab any available Azure SDK data and language models
dynamic_datas = [
    (speech_sdk_path, "azure/cognitiveservices/speech"),
]

# Seamlessly bundle all optional runtime assets directly into the application
if os.path.exists('assets'):
    dynamic_datas.append(('assets', 'assets'))

if os.path.exists('.env'):
    dynamic_datas.append(('.env', '.'))

# Optional Icon Anchor
# Place an 'app_icon.ico' directly into the assets folder to build with branding.
app_icon = 'assets/app_icon.ico' if os.path.exists('assets/app_icon.ico') else None

# -------------------------------------------------------------
# 3. Compilation Configuration
# -------------------------------------------------------------
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        # All DLLs required natively by azure-cognitiveservices-speech C bindings
        (os.path.join(speech_sdk_path, "*.dll"), "azure/cognitiveservices/speech"),
    ],
    datas=dynamic_datas,
    # System APIs and obscure hooks not implicitly traced by AST module analysis.
    hiddenimports=[
        'azure.cognitiveservices.speech',
        'azure.cognitiveservices.speech.audio',
        'azure.cognitiveservices.speech.speech',
        'azure.cognitiveservices.speech.interop',
        'google.genai',
        'google.auth',
        'pynput',
        'pynput.keyboard._win32',
        'PIL.Image',
        'PIL.ImageGrab',
        'pyaudiowpatch',
        'scipy.signal',
        'numpy',
        'dotenv',
        'ctypes',
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
    console=False,  # GUI only mode
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon,
)
