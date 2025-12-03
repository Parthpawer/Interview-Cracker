# -*- mode: python ; coding: utf-8 -*-
import os
import site
import glob
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
APP_NAME = 'AI-Assistant-with-Transcription'
ENTRY_POINT = 'main.py'
ICON_PATH = None  # Replace with 'assets/icon.ico' if you have one

# ---------------------------------------------------------------------------
# AZURE SPEECH SDK BINARIES
# ---------------------------------------------------------------------------
# Find the correct site-packages directory
speech_sdk_path = None
for sp in site.getsitepackages():
    candidate = os.path.join(sp, 'azure', 'cognitiveservices', 'speech')
    if os.path.exists(candidate):
        speech_sdk_path = candidate
        break

# Fallback if not found in getsitepackages (sometimes happens in venvs)
if not speech_sdk_path:
    # Try standard venv structure
    import sys
    candidate = os.path.join(sys.prefix, 'Lib', 'site-packages', 'azure', 'cognitiveservices', 'speech')
    if os.path.exists(candidate):
        speech_sdk_path = candidate

if not speech_sdk_path:
    print("WARNING: Could not find Azure Speech SDK path!")
else:
    print(f"Found Azure Speech SDK at: {speech_sdk_path}")

speech_binaries = []
speech_datas = []

if os.path.exists(speech_sdk_path):
    # 1. Collect DLLs/SOs/DYLIBs
    # We place them in BOTH the root and the package directory to ensure
    # the C extension can find them regardless of the loading method.
    for pattern in ('*.dll', '*.so', '*.dylib', '*.pyd'):
        for file in glob.glob(os.path.join(speech_sdk_path, pattern)):
            # Root (for PATH search)
            speech_binaries.append((file, '.'))
            # Package dir (for module loading)
            speech_binaries.append((file, 'azure/cognitiveservices/speech'))
    
    # 2. Collect Lib dependencies (if any)
    lib_path = os.path.join(speech_sdk_path, 'lib')
    if os.path.exists(lib_path):
        for pattern in ('*.dll', '*.so', '*.dylib'):
            for file in glob.glob(os.path.join(lib_path, pattern)):
                speech_binaries.append((file, '.'))
                speech_binaries.append((file, 'azure/cognitiveservices/speech'))
    
    # 3. Collect Python files (for completeness)
    for pattern in ('*.py', '*.pyi'):
        for file in glob.glob(os.path.join(speech_sdk_path, pattern)):
            speech_datas.append((file, 'azure/cognitiveservices/speech'))

# ---------------------------------------------------------------------------
# DATA FILES
# ---------------------------------------------------------------------------
extra_datas = speech_datas.copy()

# Include config/env files
if os.path.exists('.env'):
    extra_datas.append(('.env', '.'))
if os.path.exists('styles.qss'):
    extra_datas.append(('styles.qss', '.'))

# ---------------------------------------------------------------------------
# HIDDEN IMPORTS
# ---------------------------------------------------------------------------
hiddenimports = [
    # Azure
    'azure',
    'azure.cognitiveservices',
    'azure.cognitiveservices.speech',
    'azure.cognitiveservices.speech.audio',
    'azure.cognitiveservices.speech.interop',
    # Google Gemini
    'google.genai',
    'google.genai.types',
    # System / UI
    'pynput.keyboard',
    'pynput.keyboard._win32',
    'PIL',
    'PIL.ImageGrab',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    # Audio / Math
    'pyaudiowpatch',
    'scipy.signal',
    'scipy._lib.messagestream',
    'numpy',
    # Utils
    'markdown',
    'dotenv',
    'python_dotenv',
]

# ---------------------------------------------------------------------------
# ANALYSIS
# ---------------------------------------------------------------------------
a = Analysis(
    [ENTRY_POINT],
    pathex=[],
    binaries=speech_binaries,
    datas=extra_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook-azure-speech.py'],  # Critical for Azure SDK
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# ---------------------------------------------------------------------------
# EXE (Bootloader)
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [], # exclude_binaries=True forces ONEDIR mode
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,
)

# ---------------------------------------------------------------------------
# COLLECT (Folder Assembly)
# ---------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
