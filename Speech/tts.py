import os
import time
import pygame
from Speech.config import initialize_api_keys

initialize_api_keys()

def play_tts(text, child=True):
    """
    Plays text-to-speech audio. 
    If child=True, uses a higher-pitch, faster 'child' voice.
    """
    temp_file = None
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        use_ssml = False

        if openai_key and openai_key != "YOUR_OPENAI_KEY":
            try:
                from openai import OpenAI
                client = OpenAI()

                voice = "sage"

                if child:
                    use_ssml = True
                    ssml = f"""
                    <speak>
                      <prosody pitch="+6st" rate="+10%">
                        {text}
                      </prosody>
                    </speak>
                    """
                    payload = {"input": ssml}
                else:
                    payload = {"input": text}

                temp_file = f"temp_{time.time()}.mp3"
                response = client.audio.speech.create(
                    model="gpt-4o-mini-tts",
                    voice=voice,
                    **payload
                )
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
            except Exception as e:
                print(f"OpenAI TTS error: {e}, falling back to Google TTS.")

        from gtts import gTTS
        tts = gTTS(text=text, lang='en')
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
