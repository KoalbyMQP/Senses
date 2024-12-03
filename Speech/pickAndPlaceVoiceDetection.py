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

load_dotenv("Documents/GitHub/Vision-Backup/Speech/tts.env")

api_key = "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"
if not api_key:
    raise ValueError("API key not found. Please check your tts.env file.")

openai.api_key = api_key  

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
        
    def listen_and_process(self):
        try:
            with sr.Microphone() as src:
                print("Adjusting for ambient noise...")
                r.adjust_for_ambient_noise(src, duration=0.2)
                print("Listening for speech")
                audio = r.listen(src)

                try:
                    print("Converting to text...")
                    spoken_text = r.recognize_google(audio)
                    print(f"You said: {spoken_text}")
                    
                    self.current_state = State.KEYWORD_SPOTTING
                    self.speech_handler.process_command(spoken_text)
                except sr.UnknownValueError:
                    print("Sorry, could not understand the audio.")
                    self.current_state = State.IDLE
                except sr.RequestError:
                    print("Could not request results; check your internet connection.")
                    self.current_state = State.IDLE
        except Exception as e:
            print(f"Error in listen_and_process: {e}")
            self.current_state = State.IDLE

class SpeechHandler:
    def __init__(self):
        print("Initializing SpeechHandler...")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        max_retries = 3
        retry_delay = 1
        
        # Clean up any existing connections
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
                connections = proc.connections()
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
        
        while True:
            if detector.current_state == State.IDLE:
                print("System is idle. Listening for a keyword...")
                detector.listen_and_process()
            elif detector.current_state == State.COMMAND_PARSING:
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