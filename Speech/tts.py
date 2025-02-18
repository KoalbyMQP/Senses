import os
import time
import pygame
from Speech.config import initialize_api_keys


initialize_api_keys()

def play_tts(text):
    """
    Plays text-to-speech audio. Tries to use OpenAI TTS first, then falls back to Google TTS.
    """
    temp_file = None
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "YOUR_OPENAI_KEY":
            try:
                from openai import OpenAI
                client = OpenAI()
                temp_file = f"temp_{time.time()}.mp3"
                response = client.audio.speech.create(
                    model="tts-1-hd",
                    voice="sage",
                    input=text
                )
                response.stream_to_file(temp_file)
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                start_time = time.time()
                while pygame.mixer.music.get_busy():
                    if time.time() - start_time > 5:
                        print("Audio playback timeout")
                        break
                    pygame.time.Clock().tick(10)
                return
            except Exception as e:
                print(f"OpenAI TTS error: {e}, falling back to Google TTS.")
        from gtts import gTTS
        tts = gTTS(text=text, lang='en')
        temp_file = f"temp_{time.time()}.mp3"
        tts.save(temp_file)
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        start_time = time.time()
        while pygame.mixer.music.get_busy():
            if time.time() - start_time > 5:
                print("Audio playback timeout")
                break
            pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"TTS Error: {e}")
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as e:
                print(f"Error cleaning up audio file: {e}") 