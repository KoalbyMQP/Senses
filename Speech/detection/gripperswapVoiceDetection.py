import os
import time
import zmq
import requests
import speech_recognition as sr
import pygame
import sounddevice
from Speech.config import initialize_api_keys

initialize_api_keys()

from Listen.audio_capture import capture_audio
from Listen.transcription import transcribe_with_api, transcribe_with_google
from Speech.tts import play_tts
from Speech.auditing import audit_command

class SpeechHandler:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.connect("tcp://localhost:5560")  
        print("Connected to host Pi at localhost:5560")

    def send_command(self, gripper_num):
        timestamp = time.time()
        message = f"SWAP {gripper_num} {timestamp}"
        print(f"Sending command: {message}")
        self.socket.send_string(message)

class SpeechDetector:
    def __init__(self):
        self.current_state = "Idle"
        self.speech_handler = SpeechHandler()
        self.previous_gripper = None
        self.confirm_context = zmq.Context()
        self.confirm_socket = self.confirm_context.socket(zmq.SUB)
        self.confirm_socket.connect("tcp://localhost:5562")
        self.confirm_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        print("Connected to confirmation listener at localhost:5562")
        
        self.audit_prompt = """You are Finley, an elderly care robot with a gripper swapping system. Your task is to interpret user commands and return ONLY the number corresponding to the requested gripper. Here are the valid gripper mappings:

            1: default hand / main hand
            2: scoop gripper
            3: vitals gripper
            4: thermometer gripper
            5: board game gripper
            6: main gripper
            7: type 2 gripper
            8: type 3 gripper
            9: type 4 gripper
            10: type 5 gripper

            Instructions:
            - If the user says "swap gripper" or "swap" followed by a number 1-10, return that number
            - If the user specifies a gripper by name, return its corresponding number
            - If there are typos, misspellings, or extra words, try to interpret the command correctly and return the correct number
            - Return ONLY the number, with no additional text or explanation

            For example:
            Input: "swap gripper 4" → Output: 4
            Input: "swamp gripper 4" → Output: 4
            Input: "swap thermometer gripper" → Output: 4
            Input: "swap to vitals gripper please" → Output: 3
            Input: "swap type 2" → Output: 7
            Input: "gripper 8" → Output: 8
            Input: "8" → Output: 8

            Return only a single number between 1 and 10."""
            
    def parse_command(self, text):
        import re
        normalized = text.lower()
        gripper_mapping = {
            "default hand": 1,
            "scoop gripper": 2,
            "vitals gripper": 3,
            "thermometer gripper": 4,
            "board game gripper": 5,
            "main gripper": 6,
            "type 2 gripper": 7,
            "type 3 gripper": 8,
            "type 4 gripper": 9,
            "type 5 gripper": 10
        }
        for name, num in gripper_mapping.items():
            if name in normalized:
                return num
        match = re.search(r'\b(10|[1-9])\b', normalized)
        if match:
            num = int(match.group(0))
            if 1 <= num <= 10:
                return num
        return None

    def listen_and_process(self):
        audio, temp_audio = capture_audio(listen_timeout=3, phrase_time_limit=3, ambient_duration=0.2)
        if audio is None or temp_audio is None:
            return None

        # Attempt transcription using the API, then fall back to Google
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
        
        gripper_num = self.parse_command(text)
        if gripper_num is None:
            print("Couldn't directly parse command, using AI audit...")
            audited_text = audit_command(
                text,
                self.audit_prompt,
                lambda x: x.isdigit() and 1 <= int(x) <= 10,
                "GripperSwapSystem"
            )
            print(f"Processed text: '{text}' | Audited result: '{audited_text}'")
            if audited_text.isdigit():
                gripper_num = int(audited_text)
                print(f"Interpreted as gripper number: {gripper_num}")
            else:
                print("Command not recognized as a valid gripper number")
                return None
        else:
            print(f"Recognized command: '{text}' mapped to gripper {gripper_num}")

        self.speech_handler.send_command(gripper_num)
        play_tts(f"Command received: switching to gripper {gripper_num}")
        self.previous_gripper = self.previous_gripper if self.previous_gripper else gripper_num
        return gripper_num

    def listen_for_confirmation(self):
        try:
            return self.confirm_socket.recv_string(flags=zmq.NOBLOCK)
        except zmq.Again:
            return None

def run_gripper_swap_detection():
    detector = SpeechDetector()
    try:
        pygame.init()
        pygame.mixer.init()
        
        print("\n===== GRIPPER SWAP VOICE DETECTION SYSTEM =====")
        print("Valid gripper numbers:")
        print("1: Default hand / Main hand")
        print("2: Scoop gripper")
        print("3: Vitals gripper")
        print("4: Thermometer gripper")
        print("5: Board game gripper") 
        print("6: Main gripper")
        print("7: Type 2 gripper")
        print("8: Type 3 gripper")
        print("9: Type 4 gripper")
        print("10: Type 5 gripper")
        print("=========================================\n")
        
        play_tts("Gripper swap system ready. Say 'swap gripper' followed by a number 1 through 10 or the name of the gripper.")
        
        while True:
            try:
                print("\nWaiting for voice command...")
                result = detector.listen_and_process()
                if result:
                    print(f"Waiting for confirmation of gripper {result}...")
                
                confirmation = None
                start_time = time.time()
                while time.time() - start_time < 5:  
                    confirmation = detector.listen_for_confirmation()
                    if confirmation:
                        parts = confirmation.split('|')
                        if parts[-1] == "success":
                            play_tts(f"Swap to {parts[0]} successful")
                        elif parts[-1] == "already_active":
                            play_tts(f"Gripper {parts[0]} already active")
                        break
                    time.sleep(0.1)
                    
                if not confirmation and result:
                    print("No confirmation received within 5 seconds")
                    
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
        run_gripper_swap_detection()
    except Exception as e:
        print(f"\n!!! VOICE DETECTION CRASHED: {str(e)} !!!")
        import traceback
        traceback.print_exc()
        input("Press Enter to close this error window...")
