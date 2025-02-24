import speech_recognition as sr
import time
import sounddevice

def capture_audio(temp_prefix="temp_audio", listen_timeout=3, phrase_time_limit=3, ambient_duration=0.2):
    """
    Captures audio from the microphone and returns a tuple (audio, temp_audio_path).
    audio: a SpeechRecognition AudioData object.
    temp_audio_path: a path to a temporary WAV file.
    """
    r = sr.Recognizer()
    print("\nListening for speech... Please speak now")
    with sr.Microphone() as source:
        print(f"Adjusting for ambient noise ({ambient_duration}s)...")
        r.adjust_for_ambient_noise(source, duration=ambient_duration)
        print(f"Ready! Listening for up to {listen_timeout}s...")
        try:
            audio = r.listen(source, timeout=listen_timeout, phrase_time_limit=phrase_time_limit)
            print("Speech detected! Processing...")
        except sr.WaitTimeoutError:
            print("Audio capture timeout - no speech detected")
            return None, None
        
        temp_audio = f"{temp_prefix}_{time.time()}.wav"
        with open(temp_audio, "wb") as f:
            f.write(audio.get_wav_data())
            
    return audio, temp_audio 