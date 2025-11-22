import threading
import numpy as np
import pyaudiowpatch as pyaudio
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
                    self.signals.transcription_update.emit(f"✅ {evt.result.text}")
            
            def canceled_cb(evt):
                error_msg = f"Recognition canceled: {evt.result.cancellation_details.reason}"
                if evt.result.cancellation_details.error_details:
                    error_msg += f" - {evt.result.cancellation_details.error_details}"
                self.signals.status_update.emit(f"Error: {error_msg}")
                self.is_transcribing = False
            
            self.speech_recognizer.recognized.connect(recognized_cb)
            self.speech_recognizer.canceled.connect(canceled_cb)
            
            self.speech_recognizer.start_continuous_recognition()
            
            p = pyaudio.PyAudio()
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            
            loopback_device = None
            if default_speakers.get("isLoopbackDevice"):
                loopback_device = default_speakers
            else:
                for loopback in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        loopback_device = loopback
                        break
            
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
            
            while self.is_transcribing:
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    
                    if device_channels == 2:
                        audio_data = audio_data.reshape(-1, 2).mean(axis=1).astype(np.int16)
                    
                    if device_rate != 16000:
                        audio_data = resample_audio(audio_data, device_rate, 16000)
                    
                    self.audio_stream.write(audio_data.tobytes())
                    
                except Exception as e:
                    pass
                
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
