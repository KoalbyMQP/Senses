import os
import time
import pygame
from Speech.config import initialize_api_keys
from openai import OpenAI

initialize_api_keys()
client = OpenAI()

HELPER_INSTRUCTIONS = """
Identity: Finley, a small, friendly helper in a senior living home.
Personality: Cheerful, patient, gentle, and eager to assist.
Affect: Warm, bright, and consistently positive.
Tone: Clear and easy to understand, with a slightly higher, softer pitch. Use natural, friendly intonation.
Emotion: Expresses gentle enthusiasm and helpfulness.
Pace: Calm and unhurried, but clear and engaging. Use short pauses for clarity.
Volume: Gentle and reassuring.
"""

def play_tts(text: str, child: bool = True):
    """
    Plays text-to-speech audio using OpenAI TTS, aiming for a friendly helper voice.
    """
    temp_file = None
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "YOUR_OPENAI_KEY":

            voice = "sage" 
            params = {
                "model": "gpt-4o-mini-tts",
                "voice": voice,
                "input": text,
            }

            if child:
                params["instructions"] = HELPER_INSTRUCTIONS

            temp_file = f"temp_{time.time()}.mp3"
            response = client.audio.speech.create(**params)
            response.stream_to_file(temp_file)
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()

            words = len(text.split())
            estimated_duration = (words / 2.5) + 1 
            max_duration = max(3, estimated_duration) 

            start = time.time()
            while pygame.mixer.music.get_busy():
                if time.time() - start > max_duration:
                    print(f"TTS playback exceeded max duration ({max_duration}s). Stopping.")
                    pygame.mixer.music.stop()
                    break
                pygame.time.Clock().tick(10)
            return

        # Fallback to Google TTS
        from gtts import gTTS
        tts = gTTS(text=text, lang="en")
        temp_file = f"temp_{time.time()}.mp3"
        tts.save(temp_file)
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()

        estimated_duration = len(text) / (10 * (1.2 if child else 1)) + 2
        max_duration = max(5, estimated_duration)
        start = time.time()
        while pygame.mixer.music.get_busy():
            if time.time() - start > max_duration:
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
