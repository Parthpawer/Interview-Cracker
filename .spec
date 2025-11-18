# -*- mode: python ; coding: utf-8 -*-
import os
import site

# Find the azure speech SDK location
site_packages = site.getsitepackages()[0]
speech_sdk_path = os.path.join(site_packages, 'azure', 'cognitiveservices', 'speech')

a = Analysis(
    ['index.py'],
    pathex=[],
    binaries=[
        (os.path.join(speech_sdk_path, '*.dll'), 'azure/cognitiveservices/speech'),
        (os.path.join(speech_sdk_path, '*.so'), 'azure/cognitiveservices/speech'),
        (os.path.join(speech_sdk_path, '*.dylib'), 'azure/cognitiveservices/speech'),
    ],
    datas=[
        (speech_sdk_path, 'azure/cognitiveservices/speech'),
    ],
    hiddenimports=[
        'azure.cognitiveservices.speech',
        'google.genai',
        'pynput.keyboard',
        'PIL',
        'pyaudiowpatch',
        'scipy.signal',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AI-Assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
