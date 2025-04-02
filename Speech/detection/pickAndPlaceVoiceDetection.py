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
    TEMPERATURE = "Temperature"

class SpeechDetector:
    def __init__(self):
        self.current_state = State.IDLE
        self.speech_handler = None
        self.current_target = None
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.audit_prompt = """You are Finley, an elderly care robot with a pick and place system. Your task is to interpret user commands and return ONLY the name of the object to pick up or the special command.

Valid objects are:
- apple
- orange
- bottle
- cup
- remote

Special commands:
- temperature (if the user asks for temperature, body temperature, to check temperature)

Instructions:
- If the user says "pick up" followed by a valid object name, return only that object name
- If the user says things like "grab", "take", or "get" followed by a valid object, interpret it as a pick up command
- If the user asks for temperature (e.g., "get temperature", "check temperature", "body temperature"), return "temperature"
- If there are typos, misspellings, or extra words, try to interpret the command correctly
- If the user's request doesn't mention any valid object or doesn't appear to be a valid command, return "invalid"
- If the user speaks in other languages, try to understand it and follow the rules above
- Return ONLY the object name or special command, with no additional text or explanation

For example:
Input: "pick up apple" → Output: apple
Input: "grab the orange" → Output: orange
Input: "take the bottle" → Output: bottle
Input: "could you please pick up the remote control" → Output: remote
Input: "get me a cup" → Output: cup
Input: "get temperature" → Output: temperature
Input: "check my temperature" → Output: temperature
Input: "pick up the banana" → Output: invalid

Return only a single valid object name, "temperature", or "invalid"."""
    
    def parse_command(self, text):
        """Direct parsing of command without API calls"""
        normalized = text.lower()
        valid_objects = ["apple", "orange", "bottle", "cup", "remote"]
        
        temperature_phrases = ["temperature", "body temperature", "check temperature", "get temperature"]
        for phrase in temperature_phrases:
            if phrase in normalized:
                return "temperature"
        
        pick_up_words = ["pick up", "grab", "take", "get", "fetch", "bring"]
        
        for action in pick_up_words:
            if action in normalized:
                for obj in valid_objects:
                    if obj in normalized:
                        return obj
                        
        for obj in valid_objects:
            if obj in normalized and not any(word in normalized for word in ["don't", "do not", "isn't", "is not"]):
                return obj
                
        return None
        
    def listen_and_process(self):
        audio, temp_audio = capture_audio(listen_timeout=1.0, phrase_time_limit=3.0, ambient_duration=0.2)
        if audio is None or temp_audio is None:
            return
            
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
        
        object_name = self.parse_command(text)
        
        if object_name is None:
            audited_text = audit_command(
                text,
                self.audit_prompt,
                lambda x: x.lower() in ["apple", "orange", "bottle", "cup", "remote", "temperature", "invalid"],
                "PickAndPlaceSystem"
            )
            print(f"Processed text: {text} | Audited: {audited_text}")
            
            if audited_text.lower() != "invalid":
                object_name = audited_text.lower()
                if object_name == "temperature":
                    self._process_valid_command("get temperature")
                else:
                    self._process_valid_command(f"pick up {object_name}")
            else:
                print("Command not recognized.")
                play_tts("Please say pick up followed by an object name, or ask me to check temperature.")
        else:
            print(f"Directly parsed: {text} → {object_name}")
            if object_name == "temperature":
                self._process_valid_command("get temperature")
            else:
                self._process_valid_command(f"pick up {object_name}")

        self.current_state = State.IDLE

    def _process_valid_command(self, command_text):
        try:
            self.current_state = State.KEYWORD_SPOTTING
            if self.speech_handler:
                self.speech_handler.process_command(command_text)
            
            if "temperature" in command_text.lower():
                self.current_target = "temperature"
                print(f"Validated command: {command_text}")
                play_tts("I'll check your temperature")
            else:
                self.current_target = command_text.lower().split("pick up ")[-1].strip()
                print(f"Validated command: {command_text}")
                play_tts(f"I'll pick up the {self.current_target}")
        except Exception as e:
            print(f"Command processing error: {e}")

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
        lower_text = spoken_text.lower()
        
        if "temperature" in lower_text:
            message = "get temperature"
            print(f"Attempting to send command: {message}")
            try:
                self.socket.send_string(message, zmq.NOBLOCK)
                print(f"Successfully sent command: {message}")
            except zmq.error.Again:
                print("Failed to send message (would block)")
            except Exception as e:
                print(f"Error sending message: {e}")
            return
            
        if "pick up" in lower_text:
            target = lower_text.split("pick up ")[-1].strip()
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
        play_tts("I'm now listening. You can ask me to pick up objects like an apple, orange, bottle, cup, or remote.")
        
        print("\n===== PICK AND PLACE VOICE DETECTION SYSTEM =====")
        print("Valid objects:")
        print("- apple")
        print("- orange") 
        print("- bottle")
        print("- cup")
        print("- remote")
        print("=========================================\n")
        
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
    try:
        run_speech_detection()
    except Exception as e:
        print(f"\n!!! PICK AND PLACE VOICE DETECTION CRASHED: {str(e)} !!!")
        import traceback
        traceback.print_exc()
        input("Press Enter to close this error window...")