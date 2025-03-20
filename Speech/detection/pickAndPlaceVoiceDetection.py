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
from Listen.transcription import transcribe_with_api, transcribe_with_google
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

class SpeechHandler:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.connect("tcp://localhost:5558")  
        print("Connected to pick and place system at localhost:5558")

    def send_command(self, command):
        timestamp = time.time()
        message = f"{command} {timestamp}"
        print(f"Sending command: {message}")
        self.socket.send_string(message)

class SpeechDetector:
    def __init__(self):
        self.current_state = State.IDLE
        self.speech_handler = SpeechHandler()
        self.current_target = None
        
        self.audit_prompt = """You are Finley, an elderly care robot with a object manipulation system. Your task is to interpret user commands and return ONLY the name of the object to pick up or the special command.

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
        audio, temp_audio = capture_audio(listen_timeout=3, phrase_time_limit=3, ambient_duration=0.2)
        if audio is None or temp_audio is None:
            return None

        print("Transcribing speech...")
        text = transcribe_with_api(temp_audio)
        if not text:
            print("OpenAI transcription failed, trying Google Speech...")
            text = transcribe_with_google(audio)
        if os.path.exists(temp_audio):
            os.remove(temp_audio)

        if not text:
            print("No speech detected or couldn't transcribe audio")
            return None

        print(f"Transcribed text: '{text}'")
        
        command = self.parse_command(text)
        if command is None:
            print("Couldn't directly parse command, using AI audit...")
            audited_text = audit_command(
                text,
                self.audit_prompt,
                lambda x: x.lower() in ["apple", "orange", "bottle", "cup", "remote", "temperature", "invalid"],
                "PickAndPlaceSystem"
            )
            print(f"Processed text: '{text}' | Audited result: '{audited_text}'")
            
            if audited_text.lower() != "invalid":
                command = audited_text.lower()
                print(f"Interpreted as command: {command}")
            else:
                print("Command not recognized as a valid object or command")
                return None
        else:
            print(f"Recognized command: '{text}' mapped to: {command}")

        # Send the appropriate command
        if command == "temperature":
            self.speech_handler.send_command("get temperature")
            play_tts("Command received: I'll check your temperature")
        else:
            self.speech_handler.send_command(f"pick up {command}")
            play_tts(f"Command received: I'll pick up the {command}")
        
        self.current_target = command
        return command

def run_pick_and_place_detection():
    detector = SpeechDetector()
    try:
        pygame.init()
        pygame.mixer.init()
        
        print("\n===== PICK AND PLACE VOICE DETECTION SYSTEM =====")
        print("Valid commands:")
        print("- pick up apple")
        print("- pick up orange") 
        print("- pick up bottle")
        print("- pick up cup")
        print("- pick up remote")
        print("- get temperature")
        print("=========================================\n")
        
        play_tts("Pick and place system ready. You can ask me to pick up objects like an apple, orange, bottle, cup, or remote, or ask me to check temperature.")
        
        while True:
            try:
                print("\nWaiting for voice command...")
                result = detector.listen_and_process()
                if result:
                    print(f"Command '{result}' has been sent")
                    time.sleep(2)
                    
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

if __name__ == "__main__":
    try:
        run_pick_and_place_detection()
    except Exception as e:
        print(f"\n!!! PICK AND PLACE VOICE DETECTION CRASHED: {str(e)} !!!")
        import traceback
        traceback.print_exc()
        input("Press Enter to close this error window...")