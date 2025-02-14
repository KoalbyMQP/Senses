import os
from dotenv import load_dotenv

if not os.path.exists('.env'):
    with open('.env', 'w') as f:
        f.write("OPENAI_API_KEY=\nOPENROUTER_API_KEY=\n")
    print("No .env file found. A new .env file has been created with placeholder keys.")
    while True:
        resp = input("Have you filled in your keys in the .env file? (y/n): ").strip().lower()
        if resp == 'y':
            load_dotenv()
            if not os.getenv("OPENAI_API_KEY") and not os.getenv("OPENROUTER_API_KEY"):
                print("No API keys found in the .env file. Proceeding with fallbacks.")
            break
        elif resp == 'n':
            print("Proceeding without API keys. Fallbacks will be used when necessary.")
            break
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

load_dotenv()

import speech_recognition as sr
import pygame
from gtts import gTTS
import zmq
import time
import requests

class State:
    IDLE = "Idle"
    KEYWORD_SPOTTING = "Keyword Spotting"
    GRIPPER_1 = "Gripper 1"
    GRIPPER_2 = "Gripper 2"
    GRIPPER_3 = "Gripper 3"
    GRIPPER_4 = "Gripper 4"
    GRIPPER_5 = "Gripper 5"
    GRIPPER_6 = "Gripper 6"
    GRIPPER_7 = "Gripper 7"
    GRIPPER_8 = "Gripper 8"
    GRIPPER_9 = "Gripper 9"
    GRIPPER_10 = "Gripper 10"

class SpeechDetector:
    def __init__(self):
        self.current_state = State.IDLE
        self.speech_handler = SpeechHandler()
        self.previous_gripper = None
        self.confirm_context = zmq.Context()
        self.confirm_socket = self.confirm_context.socket(zmq.SUB)
        self.confirm_socket.connect("tcp://localhost:5562")
        self.confirm_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.audit_prompt = "This is a test prompt for auditing. Replace this prompt once we have the resources"
        
    def _transcribe_with_api(self, audio_path):
        import openai
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            return None
        openai.api_key = openai_api_key
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = openai.Audio.transcribe("whisper-1", audio_file)
            return transcript.get("text", "").lower()
        except Exception as e:
            print(f"OpenAI API transcription error: {e}")
            return None

    def parse_command(self, text):
        import re
        normalized = text.lower()
        gripper_mapping = {
            "default hand": 1,
            "scoop gripper": 2,
            "vitals gripper": 3,
            "thermometer gripper": 4,
            "board game gripper": 5,
            "main gripper": 6,
            "type 2 gripper": 7,
            "type 3 gripper": 8,
            "type 4 gripper": 9,
            "type 5 gripper": 10
        }
        for name, num in gripper_mapping.items():
            if name in normalized:
                return num
        match = re.search(r'\b(10|[1-9])\b', normalized)
        if match:
            num = int(match.group(0))
            if 1 <= num <= 10:
                return num
        return None

    def _audit_with_openrouter(self, text):
        if not self.openrouter_api_key:
            return text
            
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "HTTP-Referer": "http://localhost/",
                    "X-Title": "GripperSwapSystem"
                },
                json={
                    "model": "anthropic/claude-3-5-sonnet",
                    "messages": [
                        {"role": "system", "content": self.audit_prompt},
                        {"role": "user", "content": text}
                    ],
                    "temperature": 0.1
                },
                timeout=3
            )
            
            audited_text = response.json()['choices'][0]['message']['content'].strip()
            return audited_text if audited_text.isdigit() and 1 <= int(audited_text) <= 10 else "invalid"
        except Exception as e:
            print(f"Audit error: {e}")
            return text

    def _audit_command(self, text):
        import os, requests
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                response = requests.post(
                    url="https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    json={
                        "model": "o3-mini",
                        "messages": [
                            {"role": "system", "content": self.audit_prompt},
                            {"role": "user", "content": text}
                        ],
                        "temperature": 0.1
                    },
                    timeout=3
                )
                audited_text = response.json()['choices'][0]['message']['content'].strip()
                if audited_text.isdigit() and 1 <= int(audited_text) <= 10:
                    return audited_text
            except Exception as e:
                print(f"OpenAI Audit error: {e}")
        if self.openrouter_api_key:
            try:
                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_api_key}",
                        "HTTP-Referer": "http://localhost/",
                        "X-Title": "GripperSwapSystem"
                    },
                    json={
                        "model": "anthropic/claude-3-5-sonnet",
                        "messages": [
                            {"role": "system", "content": self.audit_prompt},
                            {"role": "user", "content": text}
                        ],
                        "temperature": 0.1
                    },
                    timeout=3
                )
                audited_text = response.json()['choices'][0]['message']['content'].strip()
                if audited_text.isdigit() and 1 <= int(audited_text) <= 10:
                    return audited_text
            except Exception as e:
                print(f"OpenRouter Audit error: {e}")
        print("Auditing failed, skipping auditing.")
        return text

    def listen_and_process(self):
        try:
            with sr.Microphone() as src:
                r = sr.Recognizer()
                r.adjust_for_ambient_noise(src, duration=0.2)
                print("Listening for swap commands...")
                try:
                    audio = r.listen(src, timeout=3, phrase_time_limit=3)
                except sr.WaitTimeoutError:
                    print("Audio capture timeout - no speech detected")
                    return None
                temp_audio = f"temp_audio_{time.time()}.wav"
                with open(temp_audio, "wb") as f:
                    f.write(audio.get_wav_data())
                text = self._transcribe_with_api(temp_audio)
                if not text:
                    try:
                        text = r.recognize_google(audio).lower()
                    except (sr.UnknownValueError, sr.RequestError):
                        pass
                if os.path.exists(temp_audio):
                    os.remove(temp_audio)
                if not text:
                    print("No speech detected")
                    return None

                gripper_num = self.parse_command(text)
                if gripper_num is None:
                    audited_text = self._audit_command(text)
                    print(f"Processed text: {text} | Audited: {audited_text}")
                    if audited_text.isdigit():
                        gripper_num = int(audited_text)
                    else:
                        return None
                else:
                    print(f"Recognized command: {text} mapped to gripper {gripper_num}")

                self.speech_handler.send_command(gripper_num)
                play_tts(f"Command received: switching to gripper {gripper_num}")
                self.previous_gripper = self.previous_gripper if self.previous_gripper else gripper_num
                return gripper_num
        except Exception as e:
            print(f"Critical error in audio processing: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def listen_for_confirmation(self):
        try:
            return self.confirm_socket.recv_string(flags=zmq.NOBLOCK)
        except zmq.Again:
            return None

class SpeechHandler:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.connect("tcp://localhost:5560")  
        print("Connected to host Pi at localhost:5560")

    def send_command(self, gripper_num):
        timestamp = time.time()
        message = f"SWAP {gripper_num} {timestamp}"
        print(f"Sending command: {message}")
        self.socket.send_string(message)

def run_gripper_swap_detection():
    detector = SpeechDetector()
    try:
        pygame.init()
        pygame.mixer.init()
        
        play_tts("Gripper swap system ready. Say 'swap gripper' followed by a number 1 through 10 or the name of the gripper.")
        
        while True:
            try:
                result = detector.listen_and_process()
                confirmation = None
                start_time = time.time()
                while time.time() - start_time < 5:  
                    confirmation = detector.listen_for_confirmation()
                    if confirmation:
                        parts = confirmation.split('|')
                        if parts[-1] == "success":
                            play_tts(f"Swap to {parts[0]} successful")
                        elif parts[-1] == "already_active":
                            play_tts(f"Gripper {parts[0]} already active")
                        break
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\nExiting by user request...")
                break
            except Exception as e:
                print(f"Main loop error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)
                
    finally:
        pygame.mixer.quit()
        pygame.quit()

def play_tts(text):
    try:
        import os, time, pygame, requests
        openai_key = os.getenv("OPENAI_API_KEY")
        temp_file = None
        if openai_key:
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

if __name__ == "__main__":
    try:
        run_gripper_swap_detection()
    except Exception as e:
        print(f"\n!!! VOICE DETECTION CRASHED: {str(e)} !!!")
        import traceback
        traceback.print_exc()
        input("Press Enter to close this error window...")
