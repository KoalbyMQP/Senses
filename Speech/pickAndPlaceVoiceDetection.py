import os
from dotenv import load_dotenv
import openai
import speech_recognition as sr
import pygame
from gtts import gTTS
import os

load_dotenv("Documents/GitHub/RaspberryPi-Code_24-25/test/Speech/tts.env")

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
def listen_and_process():
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
            process_command(spoken_text)
        except sr.UnknownValueError:
            print("Sorry, could not understand the audio.")
        except sr.RequestError:
            print("Could not request results; check your internet connection.")

def process_command(spoken_text):
    global current_state

    # Check for keywords and transition to specific object states
    # apple orange bottle cup and remote
    if "pick up apple" in spoken_text.lower():
        current_state = State.APPLE
        handle_apple()
    elif "pick up orange" in spoken_text.lower():
        current_state = State.ORANGE
        handle_orange()
    elif "pick up bottle" in spoken_text.lower():
        current_state = State.BOTTLE
        handle_bottle()
    elif "pick up cup" in spoken_text.lower():
        current_state = State.CUP
        handle_cup()
    elif "pick up remote" in spoken_text.lower():
        current_state = State.REMOTE
        handle_remote()
    else:
        current_state = State.COMMAND_PARSING
        play_tts("Command not recognized. Please try again.")

def handle_apple():
    print("Entering Apple state...")
    play_tts("Picking up the apple now.")

def handle_orange():
    print("Entering Orange state...")
    play_tts("Picking up the orange now.")

def handle_bottle():
    print("Entering bottle state...")
    play_tts("Picking up the bottle now.")

def handle_cup():
    print("Entering cup state...")
    play_tts("Picking up the cup now.")

def handle_remote():
    print("Entering remote state...")
    play_tts("Picking up the remote now.")

if __name__ == "__main__":
    play_tts("Hi! I'm Finley, your personal assistant.")

    while True:
        if current_state == State.IDLE:
            print("System is idle. Listening for a keyword...")
            listen_and_process()
        elif current_state == State.COMMAND_PARSING:
            print("Returning to idle state...")
            current_state = State.IDLE