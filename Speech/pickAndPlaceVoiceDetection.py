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

load_dotenv("Documents/GitHub/Vision-Backup/Speech/tts.env")

api_key = "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"
if not api_key:
    raise ValueError("API key not found. Please check your tts.env file.")

openai.api_key = api_key  

r = sr.Recognizer()
pygame.init()
pygame.mixer.init()

class State:
    IDLE = "Idle"
    KEYWORD_SPOTTING = "Keyword Spotting"
    COMMAND_PARSING = "Command Parsing"
    APPLE = "Apple"
    ORANGE = "Orange"
    BOTTLE = "Bottle"
    CUP = "Cup"
    REMOTE = "Remote"

current_state = State.IDLE

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

# Listen for speech and process it
def listen_and_process(speech_handler):
    global current_state
    with sr.Microphone() as src:
        print("Adjusting for ambient noise...")
        r.adjust_for_ambient_noise(src, duration=0.2)
        print("Listening for speech")
        audio = r.listen(src)

        try:
            print("Converting to text...")
            spoken_text = r.recognize_google(audio)
            print(f"You said: {spoken_text}")
            
            current_state = State.KEYWORD_SPOTTING
            speech_handler.process_command(spoken_text)
        except sr.UnknownValueError:
            print("Sorry, could not understand the audio.")
        except sr.RequestError:
            print("Could not request results; check your internet connection.")

class SpeechHandler:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        max_retries = 3
        retry_delay = 1
        
        # Clean up any existing connections
        self._cleanup_port()
        
        for attempt in range(max_retries):
            try:
                self.socket.bind("tcp://*:6325")
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
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.connections():
                    if hasattr(conn.laddr, 'port') and conn.laddr.port == 6325:
                        psutil.Process(proc.pid).terminate()
                        time.sleep(0.1)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    def process_command(self, spoken_text):
        if "pick up" in spoken_text.lower():
            self.socket.send_string(spoken_text.lower())
            
            if "apple" in spoken_text.lower():
                current_state = State.APPLE
                self.handle_apple()
            elif "orange" in spoken_text.lower():
                current_state = State.ORANGE
                self.handle_orange()
            elif "bottle" in spoken_text.lower():
                current_state = State.BOTTLE
                self.handle_bottle()
            elif "cup" in spoken_text.lower():
                current_state = State.CUP
                self.handle_cup()
            elif "remote" in spoken_text.lower():
                current_state = State.REMOTE
                self.handle_remote()
        else:
            current_state = State.COMMAND_PARSING
            play_tts("Command not recognized. Please try again.")

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
    try:
        speech_handler = SpeechHandler()
        pygame.init()
        pygame.mixer.init()
        play_tts("Hi! I'm Finley, your personal assistant.")
        
        while True:
            if current_state == State.IDLE:
                print("System is idle. Listening for a keyword...")
                listen_and_process(speech_handler)
            elif current_state == State.COMMAND_PARSING:
                print("Returning to idle state...")
                current_state = State.IDLE
    except KeyboardInterrupt:
        print("\nExiting speech detection...")
    except Exception as e:
        print(f"Error in speech detection: {e}")
    finally:
        pygame.quit()
        speech_handler.cleanup()

if __name__ == "__main__":
    run_speech_detection()