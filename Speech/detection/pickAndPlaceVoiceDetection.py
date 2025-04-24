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
import threading

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
- ALWAYS try to match speech recognition errors to the closest valid object, even if not explicitly listed below
- Use both phonetic similarity and meaning to match unclear words to valid objects
- Some common examples of speech recognition errors to watch for:
  - Words like "cop", "cub", "pup" should be matched to "cup"
  - Words like "battle", "boddle" should be matched to "bottle"
  - Words like "orang", "oringe" should be matched to "orange"
  - Words like "remoke", "revoke", "emote" should be matched to "remote"
  - Words like "appo", "appull" should be matched to "apple"
- Even for words not in these examples, try to match to the closest valid object based on how they sound
- Be especially forgiving of speech variations, accents, and imprecise pronunciations
- If the user's request doesn't mention any valid object or doesn't appear to be a valid command, AND you tried following everything in the rules above, only then returns "invalid" as a last resort.
- If the user speaks in other languages, try to understand it and follow the rules above
- Return ONLY the object name or special command, with no additional text or explanation

For example:
Input: "pick up apple" → Output: apple
Input: "grab the orange" → Output: orange
Input: "take the bottle" → Output: bottle
Input: "could you please pick up the remote control" → Output: remote
Input: "get me a cup" → Output: cup
Input: "pick up cop" → Output: cup
Input: "please give revoke" → Output: remote
Input: "get temperature" → Output: temperature
Input: "check my temperature" → Output: temperature
Input: "pick up the banana" → Output: invalid

Return only a single valid object name, "temperature", or "invalid"."""
        self.paused = False
        self._setup_control_socket()
    
    def _setup_control_socket(self):
        self.control_context = zmq.Context()
        self.control_socket = self.control_context.socket(zmq.SUB)
        self.control_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.control_socket.connect("tcp://localhost:5561")  

        threading.Thread(target=self._control_listener, daemon=True).start()

    def _control_listener(self):
        while True:
            try:
                cmd = self.control_socket.recv_string()
                if cmd == "pause":
                    print(f"SpeechDetector: Paused by control command. Setting self.paused = True")
                    self.paused = True
                elif cmd == "resume":
                    print(f"SpeechDetector: Resumed by control command. Setting self.paused = False")
                    self.paused = False
            except zmq.error.Again: 
                pass 
            except Exception as e:
                print(f"Control socket error: {e}")

    def parse_command(self, text):
        """Direct parsing of command with basic phonetic/error matching."""
        normalized = text.lower()
        
        object_variations = {
            "apple": ["apple", "appo", "appull"],
            "orange": ["orange", "orang", "oringe"],
            "bottle": ["bottle", "battle", "boddle"],
            "cup": ["cup", "cop", "cub", "pup"],
            "remote": ["remote", "remoke", "revoke", "emote"]
        }
        valid_objects = list(object_variations.keys())
        
        temperature_phrases = ["temperature", "body temperature", "check temperature", "get temperature"]
        for phrase in temperature_phrases:
            if phrase in normalized:
                return "temperature"
        
        pick_up_words = ["pick up", "grab", "take", "get", "fetch", "bring"]
        found_action = any(action in normalized for action in pick_up_words)
        found_object = None

        for canonical_obj, variations in object_variations.items():
            for var in variations:
                if var in normalized:
                    found_object = canonical_obj
                    break 
            if found_object:
                break 

        if found_action and found_object:
            return found_object

        if found_object and not any(word in normalized for word in ["don't", "do not", "isn't", "is not", "not"]):
            return found_object
                
        return None
        
    def listen_and_process(self):
        print(f"listen_and_process called. Current self.paused state: {self.paused}") 
        if self.paused:
            print("SpeechDetector is paused. Skipping listen cycle.")
            time.sleep(0.1)
            return
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
            self.speech_handler.send_face_command("curious") # Face: Sad if transcription failed
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
                self.speech_handler.send_face_command("curious") # Face: Sad if invalid command
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
            self.speech_handler.send_face_command("curious") # Face: Sad on error
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
                else:
                    time.sleep(retry_delay)
                    self._cleanup_port(5558)

        # Connect face socket
        try:
            print("Attempting to connect face publisher to tcp://localhost:5563")
            self.face_publisher.connect("tcp://localhost:5563")
            print("Connected to face interface socket at localhost:5563")
        except Exception as e:
             print(f"Error connecting to face interface: {e}. Face commands will not be sent.")
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
                    if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port:
                        print(f"Terminating process {proc.info['name']} (PID: {proc.info['pid']}) using port {port}")
                        psutil.Process(proc.info['pid']).terminate()
                        time.sleep(0.5) 
                        cleaned = True
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
                print(f"Sending face command: {emotion_command}")
                self.face_publisher.send_string(emotion_command, zmq.NOBLOCK)
            except zmq.error.Again:
                 print(f"Warning: Face command '{emotion_command}' send would block.")
            except Exception as e:
                print(f"Error sending face command '{emotion_command}': {e}")

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
        play_tts("I'm now listening. You can ask me to pick up objects like an apple, orange, bottle, cup, or remote OR ask me to check your temperature.")
        
        print("\n===== PICK AND PLACE VOICE DETECTION SYSTEM =====")
        print("Valid objects:")
        print("- apple")
        print("- orange") 
        print("- bottle")
        print("- cup")
        print("- remote")
        print("=========================================\n")
        
        while True:
            detector.listen_and_process()
            time.sleep(1) 

    except KeyboardInterrupt:
        print("\nExiting speech detection...")
        if detector.speech_handler:
            detector.speech_handler.send_face_command("neutral") # Set face to neutral on exit
    except Exception as e:
        print(f"Error in speech detection: {e}")
        if detector.speech_handler:
             detector.speech_handler.send_face_command("curious") # Set face to sad on error
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
