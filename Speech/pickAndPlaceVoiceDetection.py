import os
from dotenv import load_dotenv
import openai
import speech_recognition as sr
import pygame
from gtts import gTTS
import os
import zmq
import time
import psutil
import multiprocessing
import sys
import warnings
import logging
import whisper
import requests

r = sr.Recognizer()
pygame.init()
pygame.mixer.init()

def play_tts(text):
    tts = gTTS(text=text, lang='en')
    output_file = "output.mp3"
    tts.save(output_file)
    pygame.mixer.music.load(output_file)
    pygame.mixer.music.play()
    
    # Wait for playback to finish
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

    pygame.mixer.music.unload()
    os.remove(output_file)
    
class State:
    IDLE = "Idle"
    KEYWORD_SPOTTING = "Keyword Spotting"
    COMMAND_PARSING = "Command Parsing"
    APPLE = "Apple"
    ORANGE = "Orange"
    BOTTLE = "Bottle"
    CUP = "Cup"
    REMOTE = "Remote"

class SpeechDetector:
    def __init__(self):
        self.current_state = State.IDLE
        self.speech_handler = None
        self.current_target = None
        self.whisper_model = self._load_whisper_model()
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.audit_prompt = """Analyze this command for a robotic pick-and-place system. 
        Validate if it contains a request to pick up one of: apple, orange, bottle, cup, remote.
        Consider:
        1. Direct commands ("Pick up the apple")
        2. Implicit requests ("Grab the orange")
        3. Error correction ("I meant the bottle")
        4. Language translation (original may be non-English)
        5. Alternative phrasings ("Take the remote control")
        
        Respond ONLY with the object name if valid, or 'invalid' otherwise."""
        
    def _load_whisper_model(self):
        try:
            return whisper.load_model("turbo")
        except Exception as e:
            print(f"Whisper load failed: {e}. Using Google fallback")
            return None

    def _transcribe_with_whisper(self, audio_path):
        try:
            if not self.whisper_model:
                return None
                
            audio = whisper.load_audio(audio_path)
            audio = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(audio).to(self.whisper_model.device)
            
            options = whisper.DecodingOptions(task="translate")
            result = whisper.decode(self.whisper_model, mel, options)
            return result.text.lower()
        except Exception as e:
            print(f"Whisper error: {e}")
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
                    "X-Title": "PickAndPlaceSystem"
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
            
            audited_text = response.json()['choices'][0]['message']['content'].strip().lower()
            valid_objects = ["apple", "orange", "bottle", "cup", "remote"]
            return audited_text if audited_text in valid_objects else "invalid"
        except Exception as e:
            print(f"Audit error: {e}")
            return text

    def listen_and_process(self):
        try:
            with sr.Microphone() as src:
                print("Adjusting for ambient noise...")
                r.adjust_for_ambient_noise(src, duration=0.2)
                print("Listening for speech")
                
                try:
                    audio = r.listen(src, timeout=1.0, phrase_time_limit=3.0)
                except sr.WaitTimeoutError:
                    return

                # Save audio to temp file for Whisper processing
                temp_audio = f"temp_audio_{time.time()}.wav"
                with open(temp_audio, "wb") as f:
                    f.write(audio.get_wav_data())

                text = None
                # Try Whisper first
                if self.whisper_model:
                    text = self._transcribe_with_whisper(temp_audio)
                
                # Fallback to Google if Whisper fails
                if not text:
                    try:
                        text = r.recognize_google(audio).lower()
                    except (sr.UnknownValueError, sr.RequestError):
                        pass

                # Cleanup temp file
                if os.path.exists(temp_audio):
                    os.remove(temp_audio)

                if not text:
                    print("No speech detected")
                    return

                # Audit with OpenRouter
                audited_text = self._audit_with_openrouter(text)
                print(f"Processed text: {text} | Audited: {audited_text}")

                # Handle audit results
                if audited_text != "invalid":
                    valid_command = f"pick up {audited_text}"
                    self._process_valid_command(valid_command)
                else:
                    if "pick up" in text.lower() or any(word in text.lower() for word in ["grab", "take", "get"]):
                        self._handle_object_recognition(text)
                    else:
                        print("Command not recognized.")
                        play_tts("Please say pick up followed by an object name.")

        except Exception as e:
            print(f"Error in listen_and_process: {e}")
        
        self.current_state = State.IDLE

    def _process_valid_command(self, command_text):
        try:
            self.current_state = State.KEYWORD_SPOTTING
            self.speech_handler.process_command(command_text)
            self.current_target = command_text.lower().split("pick up ")[-1].strip()
            print(f"Validated command: {command_text}")
        except Exception as e:
            print(f"Command processing error: {e}")

    def _handle_object_recognition(self, text):
        object_map = {
            "apple": State.APPLE,
            "orange": State.ORANGE,
            "bottle": State.BOTTLE,
            "cup": State.CUP,
            "remote": State.REMOTE
        }
        
        detected_object = next(
            (obj for obj in object_map if obj in text.lower()),
            None
        )
        
        if detected_object:
            self._process_valid_command(f"pick up {detected_object}")
        else:
            print("Valid object not detected")
            play_tts("Please specify a valid object: apple, orange, bottle, cup, or remote.")

class SpeechHandler:
    def __init__(self):
        print("Initializing SpeechHandler...")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        max_retries = 3
        retry_delay = 1
        
        self._cleanup_port()
        
        for attempt in range(max_retries):
            try:
                print(f"Attempting to bind to port 5558 (attempt {attempt + 1})")
                self.socket.bind("tcp://*:5558")
                print("Speech ZMQ initialized successfully")
                break
            except zmq.error.ZMQError as e:
                print(f"ZMQ initialization attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delay)
                self._cleanup_port()

    def _cleanup_port(self):
        """Clean up the ZMQ port"""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                connections = proc.net_connections()
                for conn in connections:
                    if hasattr(conn, 'laddr') and hasattr(conn.laddr, 'port') and conn.laddr.port == 5558:
                        psutil.Process(proc.pid).terminate()
                        time.sleep(0.1)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    def process_command(self, spoken_text):
        if "pick up" in spoken_text.lower():
            target = spoken_text.lower().split("pick up ")[-1].strip()
            message = f"pick up {target}"
            print(f"Attempting to send command: {message}")
            try:
                self.socket.send_string(message, zmq.NOBLOCK)
                print(f"Successfully sent command: {message}")
            except zmq.error.Again:
                print("Failed to send message (would block)")
            except Exception as e:
                print(f"Error sending message: {e}")

    def cleanup(self):
        """Clean up ZMQ resources"""
        try:
            if hasattr(self, 'socket'):
                self.socket.close()
            if hasattr(self, 'context'):
                self.context.term()
        except Exception as e:
            print(f"Error during cleanup: {e}")

def handle_apple():
    print("Entering Apple state...")
    play_tts("Picking up the apple now.")

def handle_orange():
    print("Entering Orange state...")
    play_tts("Picking up the orange now.")

def handle_bottle():
    print("Entering Bottle state...")
    play_tts("Picking up the bottle now.")

def handle_cup():
    print("Entering Cup state...")
    play_tts("Picking up the cup now.")

def handle_remote():
    print("Entering Remote state...")
    play_tts("Picking up the remote now.")

def run_speech_detection():
    detector = SpeechDetector()
    try:
        detector.speech_handler = SpeechHandler()
        pygame.init()
        pygame.mixer.init()
        
        play_tts("Hi! I'm Finley, your personal assistant.")
        print("Waiting 5 seconds before starting to listen...")
        time.sleep(5)
        play_tts("I'm now listening. Please speak clearly.")
        
        while True:
            if detector.current_state == State.IDLE:
                detector.listen_and_process()
                time.sleep(0.1)
            else:
                print("Returning to idle state...")
                detector.current_state = State.IDLE
                
    except KeyboardInterrupt:
        print("\nExiting speech detection...")
    except Exception as e:
        print(f"Error in speech detection: {e}")
    finally:
        pygame.quit()
        if detector.speech_handler:
            detector.speech_handler.cleanup()

if __name__ == "__main__":
    run_speech_detection()