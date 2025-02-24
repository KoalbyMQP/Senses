import os
import speech_recognition as sr
import sounddevice

# Cache for the Whisper model
_whisper_model = None

def load_whisper_model(model_name="turbo"):
    """
    Loads and caches the local Whisper model.
    """
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            _whisper_model = whisper.load_model(model_name)
        except Exception as e:
            print(f"Whisper load failed: {e}. Using fallback.")
            _whisper_model = None
    return _whisper_model

def transcribe_with_api(audio_path, provider="openai"):
    """
    Transcribes audio using OpenAI's Whisper API.
    """
    if provider == "openai":
        try:
            from openai import OpenAI
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                print("OpenAI API key not found in environment variables")
                return None
                
            client = OpenAI(api_key=openai_api_key)
            with open(audio_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            return transcript.text.lower()
        except Exception as e:
            print(f"OpenAI API transcription error: {e}")
            return None
    return None

def transcribe_with_google(audio, recognizer=None):
    """
    Transcribes audio using the Google Speech Recognition.
    """
    if recognizer is None:
        recognizer = sr.Recognizer()
    try:
        return recognizer.recognize_google(audio).lower()
    except (sr.UnknownValueError, sr.RequestError) as e:
        print(f"Google transcription error: {e}")
        return None

def transcribe_with_whisper(audio_path, model_name="turbo"):
    """
    Transcribes audio using a local Whisper model.
    """
    model = load_whisper_model(model_name)
    if not model:
        return None
    try:
        import whisper
        audio = whisper.load_audio(audio_path)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(model.device)
        options = whisper.DecodingOptions(task="translate")
        result = whisper.decode(model, mel, options)
        return result.text.lower()
    except Exception as e:
        print(f"Whisper transcription error: {e}")
        return None 