import os
import time
import pygame
from Speech.config import initialize_api_keys
from openai import OpenAI

initialize_api_keys()
client = OpenAI()

# Toddler‐style instructions. Might or might not work honestly idk
TODDLER_INSTRUCTIONS = """
Identity: A warm, playful two-year-old helper in a senior living home—like a beloved grandchild.
Affect: Bright and bubbly, with gentle curiosity and an ever-present smile in their voice.
Tone: Simple, enthusiastic, and soothing—short sentences, clear pauses, and natural giggles.
Emotion: Loving and affectionate, eager to help, with genuine excitement at every task.
Pronunciation: Slightly higher pitch, occasional innocent mispronunciations (“pway” for “play”), and soft stumbles.
Pace: Lively but unhurried—just fast enough to sound excited, with brief pauses to let the listener respond.
Volume: Gentle and reassuring, never too loud.
Pauses: Soft breaths between phrases, extra pause before asking a question to invite a reply.
"""

def play_tts(text: str, child: bool = True):
    """
    Plays text-to-speech audio.
    Has voice switching but we shouldnt use it for now
    """
    temp_file = None
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "YOUR_OPENAI_KEY":
            voice = "sage" if child else "sage"
            params = {
                "model": "gpt-4o-mini-tts",
                "voice": voice,
                "input": text,
            }
            if child:
                params["instructions"] = TODDLER_INSTRUCTIONS

            temp_file = f"temp_{time.time()}.mp3"
            response = client.audio.speech.create(**params)
            response.stream_to_file(temp_file)
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()

            factor = 1.2 if child else 1.0
            estimated_duration = (len(text) / 15 + 2) * factor
            max_duration = max(5, estimated_duration)
            start = time.time()
            while pygame.mixer.music.get_busy():
                if time.time() - start > max_duration:
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
