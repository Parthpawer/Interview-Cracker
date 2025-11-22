# -*- mode: python ; coding: utf-8 -*-
import os
import site
import glob

# Find the azure speech SDK location
site_packages = site.getsitepackages()[0]
speech_sdk_path = os.path.join(site_packages, 'azure', 'cognitiveservices', 'speech')

# Collect Azure Speech SDK binaries
speech_binaries = []
if os.path.exists(speech_sdk_path):
    # Find all DLL files (including dependencies)
    for dll in glob.glob(os.path.join(speech_sdk_path, '*.dll')):
        speech_binaries.append((dll, '.'))
    # Find all SO files (Linux)
    for so in glob.glob(os.path.join(speech_sdk_path, '*.so')):
        speech_binaries.append((so, '.'))
    # Find all DYLIB files (macOS)
    for dylib in glob.glob(os.path.join(speech_sdk_path, '*.dylib')):
        speech_binaries.append((dylib, '.'))
    
    # Also check for DLLs in subdirectories
    lib_path = os.path.join(speech_sdk_path, 'lib')
    if os.path.exists(lib_path):
        for dll in glob.glob(os.path.join(lib_path, '*.dll')):
            speech_binaries.append((dll, '.'))

a = Analysis(
    ['ai_assistant_resize.py'],
    pathex=[],
    binaries=speech_binaries,
    datas=[
        # Include entire speech SDK folder to get all resources
        (speech_sdk_path, 'azure/cognitiveservices/speech'),
    ] if os.path.exists(speech_sdk_path) else [],
    hiddenimports=[
        'azure.cognitiveservices.speech',
        'azure.cognitiveservices.speech.audio',
        'azure.cognitiveservices.speech.interop',
        'google.genai',
        'google.genai.types',
        'pynput.keyboard',
        'pynput.keyboard._win32',
        'PIL',
        'PIL.ImageGrab',
        'pyaudiowpatch',
        'scipy.signal',
        'numpy',
        'markdown',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# ONE-FILE CONFIGURATION
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,      # INCLUDED: All binaries packed into exe
    a.datas,         # INCLUDED: All data files packed into exe
    [],
    name='AI-Assistant-with-Transcription',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,        # Compress the exe
    upx_exclude=[],
    runtime_tmpdir=None,  # Extract to temp on each run
    console=False,   # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# NO COLLECT section for one-file build

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AI-Assistant-with-Transcription',  # CHANGED: More descriptive name
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # OPTIONAL: Add icon='icon.ico' if you have one
)