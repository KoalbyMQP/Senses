import os
import time
import zmq
import psutil
import pygame
import warnings
import logging
import requests
import speech_recognition as sr
import sounddevice
from Speech.config import initialize_api_keys

initialize_api_keys()

from Listen.audio_capture import capture_audio
from Listen.transcription import transcribe_with_api, transcribe_with_google, transcribe_with_whisper
from Speech.tts import play_tts
from Speech.auditing import audit_command  

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
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.audit_prompt = """Analyze this command for a robotic pick-and-place system. 
Validate if it contains a request to pick up one of: apple, orange, bottle, cup, remote.
Respond ONLY with the object name if valid, or 'invalid' otherwise."""
        
    def listen_and_process(self):
        audio, temp_audio = capture_audio(listen_timeout=1.0, phrase_time_limit=3.0, ambient_duration=0.2)
        if audio is None or temp_audio is None:
            return
        # Attempt transcription: API -> Whisper -> Google
        text = transcribe_with_api(temp_audio)
        if not text:
            text = transcribe_with_whisper(temp_audio)
        if not text:
            text = transcribe_with_google(audio)
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
        if not text:
            print("No speech detected")
            return
        
        valid_objects = ["apple", "orange", "bottle", "cup", "remote"]
        audited_text = audit_command(
            text,
            self.audit_prompt,
            lambda x: x.lower() in valid_objects,
            "PickAndPlaceSystem"
        )
        print(f"Processed text: {text} | Audited: {audited_text}")
        
        if audited_text.lower() != "invalid":
            valid_command = f"pick up {audited_text}"
            self._process_valid_command(valid_command)
        else:
            if "pick up" in text.lower() or any(word in text.lower() for word in ["grab", "take", "get"]):
                self._handle_object_recognition(text)
            else:
                print("Command not recognized.")
                play_tts("Please say pick up followed by an object name.")

        self.current_state = State.IDLE

    def _process_valid_command(self, command_text):
        try:
            self.current_state = State.KEYWORD_SPOTTING
            if self.speech_handler:
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
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                connections = proc.net_connections()
                for conn in connections:
                    if hasattr(conn, 'laddr') and conn.laddr and len(conn.laddr) >= 2 and conn.laddr.port == 5558:
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
        try:
            if hasattr(self, 'socket'):
                self.socket.close()
            if hasattr(self, 'context'):
                self.context.term()
        except Exception as e:
            print(f"Error during cleanup: {e}")

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