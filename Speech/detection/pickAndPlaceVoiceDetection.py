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
- If the user says "pick up" followed by a valid object name (or something that sounds similar), return only that object name
- If the user says things like "grab", "take", or "get" followed by a valid object (or something that sounds similar), interpret it as a pick up command
- If the user asks for temperature or mentions temperature checking, return "temperature"
- Pay special attention to words that sound similar to valid objects:
  - Words that sound like "cup" (such as "cop", "cub")
  - Words that sound like "bottle" (such as "boddle", "battle")
  - Words that sound like "apple" (such as "appo", "happle")
  - Words that sound like "orange" (such as "oringe", "horinge")
  - Words that sound like "remote" (such as "remoke", "rimote")
- Consider regional accents, speech impediments, and non-native English speakers when interpreting commands
- If the user's request doesn't mention any valid object or doesn't appear to be asking for temperature, return "invalid"
- Return ONLY the object name or special command, with no additional text or explanation

For example:
Input: "pick up apple" → Output: apple
Input: "grab the orange" → Output: orange
Input: "take the bottle" → Output: bottle
Input: "pick up the cop" → Output: cup
Input: "get me a cup" → Output: cup
Input: "check temperature" → Output: temperature
Input: "temperature" → Output: temperature
Input: "give me the remoke" → Output: remote
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
        self.speech_handler.send_face_command("listening") # Face: Listening
        audio, temp_audio = capture_audio(listen_timeout=1.0, phrase_time_limit=3.0, ambient_duration=0.2)
        if audio is None or temp_audio is None:
            self.speech_handler.send_face_command("neutral") # Face: Back to neutral if no audio
            return

        print("Transcribing speech...")
        self.speech_handler.send_face_command("thinking") # Face: Thinking
        text = transcribe_with_api(temp_audio)
        if not text:
            text = transcribe_with_whisper(temp_audio)
        if not text:
            text = transcribe_with_google(audio)
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
        if not text:
            print("No speech detected")
            self.speech_handler.send_face_command("sad") # Face: Sad if transcription failed
            time.sleep(1.5)
            self.speech_handler.send_face_command("neutral")
            return

        object_name = self.parse_command(text)

        if object_name is None:
            self.speech_handler.send_face_command("thinking") # Face: Thinking (auditing)
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
                self.speech_handler.send_face_command("sad") # Face: Sad if invalid command
                time.sleep(1.5)
                self.speech_handler.send_face_command("neutral")
        else:
            print(f"Directly parsed: {text} → {object_name}")
            if object_name == "temperature":
                self._process_valid_command("get temperature")
            else:
                self._process_valid_command(f"pick up {object_name}")

        # State reset is handled within _process_valid_command or if invalid

    def _process_valid_command(self, command_text):
        try:
            self.current_state = State.KEYWORD_SPOTTING
            if self.speech_handler:
                self.speech_handler.process_command(command_text) # Send to main demo logic

            if "temperature" in command_text.lower():
                self.current_target = "temperature"
                print(f"Validated command: {command_text}")
                play_tts("I'll check your temperature")
                self.speech_handler.send_face_command("neutral") # Face: Neutral after processing
            else:
                self.current_target = command_text.lower().split("pick up ")[-1].strip()
                print(f"Validated command: {command_text}")
                play_tts(f"I'll pick up the {self.current_target}")
                self.speech_handler.send_face_command("neutral") # Face: Neutral after processing

            # Transition back to IDLE *after* sending the command and TTS
            self.current_state = State.IDLE

        except Exception as e:
            print(f"Command processing error: {e}")
            self.speech_handler.send_face_command("sad") # Face: Sad on error
            time.sleep(1.5)
            self.current_state = State.IDLE # Reset state even on error
            self.speech_handler.send_face_command("neutral")

class SpeechHandler:
    def __init__(self):
        print("Initializing SpeechHandler...")
        self.context = zmq.Context()
        # Socket for commands to speech_demo.py
        self.socket = self.context.socket(zmq.PUB)
        # Socket for commands to face.py
        self.face_publisher = self.context.socket(zmq.PUB)
        max_retries = 3
        retry_delay = 1
        self._cleanup_port(5558) # Clean up command port
        self._cleanup_port(5563) # Clean up face port

        # Bind command socket
        for attempt in range(max_retries):
            try:
                print(f"Attempting to bind command socket to port 5558 (attempt {attempt + 1})")
                self.socket.bind("tcp://*:5558")
                print("Speech ZMQ command socket initialized successfully")
                break
            except zmq.error.ZMQError as e:
                print(f"ZMQ command socket initialization attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    print("!!! FAILED TO BIND COMMAND SOCKET !!!")
                    # Decide if you want to raise or just proceed without it
                    # raise # Or set self.socket = None
                else:
                    time.sleep(retry_delay)
                    self._cleanup_port(5558)

        # Connect face socket
        # Use connect for face since face.py binds
        try:
            print("Attempting to connect face publisher to tcp://localhost:5563")
            self.face_publisher.connect("tcp://localhost:5563")
            print("Connected to face interface socket at localhost:5563")
        except Exception as e:
             print(f"Error connecting to face interface: {e}. Face commands will not be sent.")
             # Close the socket if connection failed, set to None
             if self.face_publisher:
                 self.face_publisher.close()
             self.face_publisher = None


    def _cleanup_port(self, port):
        import psutil
        print(f"Checking for processes using port {port}...")
        cleaned = False
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                connections = proc.net_connections(kind='inet')
                for conn in connections:
                    # Check for listening sockets on the target port
                    if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port:
                        print(f"Terminating process {proc.info['name']} (PID: {proc.info['pid']}) using port {port}")
                        psutil.Process(proc.info['pid']).terminate()
                        time.sleep(0.5) # Give time for termination
                        cleaned = True
                        # Wait for process to terminate
                        try:
                           proc.wait(timeout=1.0)
                        except psutil.TimeoutExpired:
                            print(f"Process {proc.info['pid']} did not terminate, killing.")
                            psutil.Process(proc.info['pid']).kill()
                            time.sleep(0.1)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                 print(f"Error during port cleanup check for PID {proc.pid}: {e}")
        if cleaned:
            print(f"Finished cleanup check for port {port}.")
        else:
            print(f"No processes found listening on port {port}.")

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

    def send_face_command(self, emotion_command):
        """Send an emotion command string to the face interface."""
        if self.face_publisher:
            try:
                # print(f"Sending face command: {emotion_command}") # Optional: uncomment for verbose logging
                self.face_publisher.send_string(emotion_command, zmq.NOBLOCK)
            except zmq.error.Again:
                 print(f"Warning: Face command '{emotion_command}' send would block.")
            except Exception as e:
                print(f"Error sending face command '{emotion_command}': {e}")
        # else: # Optional: uncomment for verbose logging
        #     print(f"Skipping face command '{emotion_command}': publisher not available.")

    def cleanup(self):
        try:
            if hasattr(self, 'socket') and self.socket:
                self.socket.close()
            if hasattr(self, 'face_publisher') and self.face_publisher:
                self.face_publisher.close()
            if hasattr(self, 'context'):
                self.context.term()
            print("SpeechHandler resources cleaned up.")
        except Exception as e:
            print(f"Error during SpeechHandler cleanup: {e}")

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
        if detector.speech_handler:
            detector.speech_handler.send_face_command("neutral") # Set face to neutral on exit
    except Exception as e:
        print(f"Error in speech detection: {e}")
        if detector.speech_handler:
             detector.speech_handler.send_face_command("sad") # Set face to sad on error
             time.sleep(1.5)
             detector.speech_handler.send_face_command("neutral")
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
