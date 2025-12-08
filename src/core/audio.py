import threading
import numpy as np
try:
    import pyaudiowpatch as pyaudio
    HAS_PYAUDIOWPATCH = True
except ImportError:
    HAS_PYAUDIOWPATCH = False
    try:
        import pyaudio
    except ImportError:
        pyaudio = None
import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech.audio import AudioStreamFormat, PushAudioInputStream
from src.config import Config
from src.utils.helpers import resample_audio

class AudioTranscriber:
    """Handles audio capture and Azure Speech transcription."""
    
    def __init__(self, signals):
        self.signals = signals
        self.is_transcribing = False
        self.transcription_thread = None
        self.audio_stream = None
        self.speech_recognizer = None

    def start(self, api_key, region):
        """Start transcription."""
        if not pyaudio:
            self.signals.status_update.emit("❌ PyAudio not installed. Transcription disabled. Try: pip install pyaudio")
            return False

        if not api_key or not region:
            self.signals.status_update.emit("Error: Set Azure API key and region in Settings")
            return False

        self.is_transcribing = True
        self.signals.status_update.emit("Status: Starting transcription...")

        self.transcription_thread = threading.Thread(
            target=self._transcription_worker,
            args=(api_key, region),
            daemon=True
        )
        self.transcription_thread.start()
        return True

    def stop(self):
        """Stop transcription."""
        self.is_transcribing = False
        if self.speech_recognizer:
            try:
                self.speech_recognizer.stop_continuous_recognition()
            except:
                pass

    def _transcription_worker(self, api_key, region):
        """Worker thread for audio capture and transcription."""
        p = None
        stream = None
        
        try:
            speech_config = speechsdk.SpeechConfig(subscription=api_key, region=region)
            speech_config.speech_recognition_language = "en-US"
            
            audio_format = AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1)
            self.audio_stream = PushAudioInputStream(stream_format=audio_format)
            audio_config = speechsdk.audio.AudioConfig(stream=self.audio_stream)
            
            self.speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            
            def recognized_cb(evt):
                if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    print(f"✓ Recognized: {evt.result.text}")
                    self.signals.transcription_update.emit(f"✅ {evt.result.text}")
                elif evt.result.reason == speechsdk.ResultReason.NoMatch:
                    print(f"⚠️ No speech recognized in audio")
                    self.signals.status_update.emit("⚠️ No speech detected in that audio segment")
            
            def canceled_cb(evt):
                error_msg = f"Recognition canceled: {evt.result.cancellation_details.reason}"
                if evt.result.cancellation_details.error_details:
                    error_msg += f" - {evt.result.cancellation_details.error_details}"
                print(f"✗ {error_msg}")
                self.signals.status_update.emit(f"Error: {error_msg}")
                self.is_transcribing = False
            
            self.speech_recognizer.recognized.connect(recognized_cb)
            self.speech_recognizer.canceled.connect(canceled_cb)
            
            self.speech_recognizer.start_continuous_recognition()
            
            p = pyaudio.PyAudio()
            try:
                wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            except (AttributeError, OSError):
                self.signals.status_update.emit("Error: WASAPI not supported")
                return

            default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            
            loopback_device = None
            is_loopback = True
            if default_speakers.get("isLoopbackDevice"):
                loopback_device = default_speakers
            else:
                if hasattr(p, 'get_loopback_device_info_generator'):
                    for loopback in p.get_loopback_device_info_generator():
                        if default_speakers["name"] in loopback["name"]:
                            loopback_device = loopback
                            break
                else:
                    # Fall back to default input device (microphone) if WASAPI loopback isn't available.
                    try:
                        default_input = p.get_default_input_device_info()
                        loopback_device = default_input
                        is_loopback = False
                        msg = "⚠️ WASAPI loopback not available. Using microphone instead."
                        if not HAS_PYAUDIOWPATCH:
                            msg += " Install pyaudiowpatch for system audio: pip install pyaudiowpatch"
                        self.signals.status_update.emit(msg)
                    except Exception as e:
                        self.signals.status_update.emit(f"❌ Error: Install pyaudiowpatch or update audio drivers. Details: {str(e)}")
                        return
            
            if not loopback_device:
                self.signals.status_update.emit("Error: No loopback device found")
                return
            
            device_channels = loopback_device["maxInputChannels"]
            device_rate = int(loopback_device["defaultSampleRate"])
            
            CHUNK = 1024
            stream = p.open(
                format=pyaudio.paInt16,
                channels=device_channels,
                rate=device_rate,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=loopback_device["index"]
            )
            
            self.signals.status_update.emit("Status: Recording and transcribing...")
            silent_frames = 0
            
            while self.is_transcribing:
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    
                    if device_channels == 2:
                        audio_data = audio_data.reshape(-1, 2).mean(axis=1).astype(np.int16)
                    
                    if device_rate != 16000:
                        audio_data = resample_audio(audio_data, device_rate, 16000)
                    
                    # Check if audio has meaningful signal (not silent)
                    audio_level = np.abs(audio_data).mean()
                    if audio_level < 100:  # Very quiet threshold
                        silent_frames += 1
                        if silent_frames > 50:
                            self.signals.status_update.emit("⚠️ No sound detected. Check microphone levels or try speaking louder.")
                            silent_frames = 0
                    else:
                        silent_frames = 0
                        self.signals.status_update.emit("🎤 Recording...")
                    
                    self.audio_stream.write(audio_data.tobytes())
                    
                except Exception as e:
                    print(f"Audio capture error: {e}")
                
        except Exception as e:
            self.signals.status_update.emit(f"Error: {str(e)}")
            
        finally:
            try:
                if stream:
                    stream.stop_stream()
                    stream.close()
                if p:
                    p.terminate()
                if self.audio_stream:
                    self.audio_stream.close()
                if self.speech_recognizer:
                    self.speech_recognizer.stop_continuous_recognition()
            except:
                pass
