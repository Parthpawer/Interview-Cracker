import os
import sys
import ctypes
from glob import glob

# Runtime hook to pre-load Azure Speech SDK DLLs
# This is critical because the SDK's internal loading logic fails in frozen environments

def load_speech_dll():
    # 1. Determine the base directory
    if getattr(sys, 'frozen', False):
        # If frozen, look in the _internal directory or root
        base_dir = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
    else:
        return

    # 2. Define potential locations for the DLL
    # The DLL name is usually Microsoft.CognitiveServices.Speech.core.dll
    dll_name = "Microsoft.CognitiveServices.Speech.core.dll"
    
    search_paths = [
        base_dir,
        os.path.join(base_dir, 'azure', 'cognitiveservices', 'speech'),
        os.path.join(base_dir, '_internal', 'azure', 'cognitiveservices', 'speech'),
        os.path.join(base_dir, '_internal'),
    ]

    # 3. Search and Load
    dll_path = None
    for path in search_paths:
        candidate = os.path.join(path, dll_name)
        if os.path.exists(candidate):
            dll_path = candidate
            break
    
    if not dll_path:
        # Fallback: recursive search if not found in standard locations
        for root, dirs, files in os.walk(base_dir):
            if dll_name in files:
                dll_path = os.path.join(root, dll_name)
                break

    if dll_path:
        try:
            # Explicitly load the DLL using ctypes
            # This makes it available to the process so subsequent imports find it
            ctypes.CDLL(dll_path)
            
            # Also add its directory to the DLL search path (Python 3.8+)
            if hasattr(os, 'add_dll_directory'):
                os.add_dll_directory(os.path.dirname(dll_path))
                
            # And to the PATH environment variable
            os.environ['PATH'] = os.path.dirname(dll_path) + os.pathsep + os.environ['PATH']
            
        except Exception as e:
            # If loading fails, we print but don't crash yet; the app might still fail later
            print(f"Failed to pre-load Azure Speech DLL from {dll_path}: {e}")
    else:
        print(f"WARNING: Could not find {dll_name} in frozen bundle.")

# Execute the loader
load_speech_dll()
