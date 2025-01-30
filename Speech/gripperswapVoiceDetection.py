import os
from dotenv import load_dotenv
import speech_recognition as sr
import pygame
from gtts import gTTS
import zmq
import time

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
        
    def listen_and_process(self):
        try:
            with sr.Microphone() as src:
                r = sr.Recognizer()
                r.adjust_for_ambient_noise(src, duration=0.2)
                print("Listening for swap commands...")
                
                audio = r.listen(src, timeout=3, phrase_time_limit=3)
                text = r.recognize_google(audio).lower()
                print(f"Recognized: {text}")
                
                if "swap gripper" in text:
                    try:
                        gripper_num = int(text.split("swap gripper")[1].strip())
                        if 1 <= gripper_num <= 10:
                            self.speech_handler.send_command(gripper_num)
                            return gripper_num
                    except (ValueError, IndexError):
                        print("Invalid gripper number format")
        except Exception as e:
            print(f"Error: {e}")
        return None

class SpeechHandler:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.connect("tcp://localhost:5560")  
        print("Connected to host Pi at localhost:5560")

    def send_command(self, gripper_num):
        message = f"SWAP {gripper_num}"
        print(f"Sending command: {message}")
        self.socket.send_string(message)

def run_gripper_swap_detection():
    detector = SpeechDetector()
    pygame.init()
    pygame.mixer.init()
    
    play_tts("Gripper swap system ready. Say 'swap gripper' followed by a number 1 through 10.")
    
    while True:
        result = detector.listen_and_process()
        if result:
            play_tts(f"Swapping to gripper {result}")
        time.sleep(0.1)

def play_tts(text):
    tts = gTTS(text=text, lang='en')
    tts.save("temp.mp3")
    pygame.mixer.music.load("temp.mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    os.remove("temp.mp3")

if __name__ == "__main__":
    run_gripper_swap_detection()
