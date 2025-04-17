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
        print("Connected to host Pi command socket at localhost:5560")

        self.face_publisher = self.context.socket(zmq.PUB)
        try:
            self.face_publisher.connect("tcp://localhost:5563")
            print("Connected to face interface socket at localhost:5563")
        except Exception as e:
             print(f"Error connecting to face interface: {e}")
             self.face_publisher = None 

    def send_command(self, gripper_num):
        timestamp = time.time()
        message = f"SWAP {gripper_num} {timestamp}"
        print(f"Sending command: {message}")
        self.socket.send_string(message)

    def send_face_command(self, emotion_command):
        """Send an emotion command string to the face interface."""
        if self.face_publisher:
            try:
                print(f"Sending face command: {emotion_command}")
                self.face_publisher.send_string(emotion_command)
            except Exception as e:
                print(f"Error sending face command '{emotion_command}': {e}")

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
            - If the user says anything, interpret it and try to understand whether or not the user is trying to swap grippers. If you think they are, return the number of the gripper they want to swap to. If you think they are not, return invalid.
            - If the user specifies a gripper that is NOT in the list above, first try to interpret it and see if it can potentially match with a valid gripper command. Your interpretation should be as close as possible based on phonetics first and then meaning. The context should always be something that can be a gripper type. 
            - If you cannot interpret the command, return invalid.
            - It is ok to interpret a command as invalid, it is better to have to repeat what is said then to give the robot the wrong gripper
            - If the user says in other languages, try to understand it and follow the rules above.
            - Return ONLY the number, with no additional text or explanation

            For example:
            Input: "swap gripper 4" → Output: 4
            Input: "swamp gripper 4" → Output: 4
            Input: "swap thermometer gripper" → Output: 4
            Input: "swap to vitals gripper please" → Output: 3
            Input: "i want board game cripper" -> Output: 5
            Input: "swap type 2" → Output: 7
            Input: "gripper 8" → Output: 8
            Input: "8" → Output: 8
            Input: "swap to vinyl cripper" → Output: 3
            Input: "swap to scope gripper" → Output: 2
            

            Return only a single number between 1 and 10 or invalid."""
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
        self.speech_handler.send_face_command("listening") 
        audio, temp_audio = capture_audio(listen_timeout=3, phrase_time_limit=3, ambient_duration=0.2)
        if audio is None or temp_audio is None:
            self.speech_handler.send_face_command("neutral") 
            return None

        print("Transcribing speech...")
        self.speech_handler.send_face_command("thinking") 
        text = transcribe_with_api(temp_audio)
        if not text:
            print("OpenAI transcription failed, trying Google Speech...")
            text = transcribe_with_google(audio)
        if os.path.exists(temp_audio):
            os.remove(temp_audio)

        if not text:
            print("No speech detected or couldn't transcribe audio")
            self.speech_handler.send_face_command("sad") 
            time.sleep(2) 
            self.speech_handler.send_face_command("neutral")
            return None

        print(f"Transcribed text: '{text}'")

        gripper_num = self.parse_command(text)
        if gripper_num is None:
            print("Couldn't directly parse command, using AI audit...")
            self.speech_handler.send_face_command("thinking") 
            audited_text = audit_command(
                text,
                self.audit_prompt,
                lambda x: x.isdigit() and 1 <= int(x) <= 10 or x == "invalid", 
                "GripperSwapSystem"
            )
            print(f"Processed text: '{text}' | Audited result: '{audited_text}'")
            if audited_text.isdigit():
                gripper_num = int(audited_text)
                print(f"Interpreted as gripper number: {gripper_num}")
            else:
                print("Command not recognized as a valid gripper number after audit")
                play_tts("Sorry, I didn't understand that gripper command.")
                self.speech_handler.send_face_command("sad") 
                time.sleep(2)
                self.speech_handler.send_face_command("neutral")
                return None
        else:
            print(f"Recognized command: '{text}' mapped to gripper {gripper_num}")

        self.speech_handler.send_command(gripper_num)
        play_tts(f"Command received: switching to gripper {gripper_num}")
        self.speech_handler.send_face_command("neutral") 
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
        detector.speech_handler.send_face_command("neutral") 
        
        while True:
            try:
                print("\nWaiting for voice command...")
                detector.speech_handler.send_face_command("neutral") 
                result = detector.listen_and_process()
                if result:
                    print(f"Waiting for confirmation of gripper {result}...")
                    

                    confirmation = None
                    start_time = time.time()
                    wait_timeout = 5 
                    while time.time() - start_time < wait_timeout:
                        confirmation = detector.listen_for_confirmation()
                        if confirmation:
                            print(f"Confirmation received: {confirmation}")
                            parts = confirmation.split('|')
                            status = "unknown"
                            confirmed_gripper = "?"
                            if len(parts) > 0: confirmed_gripper = parts[0]
                            if len(parts) > 7: status = parts[7]

                            if status == "success":
                                detector.speech_handler.send_face_command("happy")
                                play_tts(f"Swap to {confirmed_gripper} successful")
                                time.sleep(2) 
                            elif status == "already_active":
                                detector.speech_handler.send_face_command("neutral") 
                                play_tts(f"Gripper {confirmed_gripper} already active")
                                time.sleep(2)
                            else:
                                detector.speech_handler.send_face_command("sad") 
                                play_tts(f"Received unclear confirmation status: {status}")
                                time.sleep(2)
                            break
                        time.sleep(0.1)

                    if not confirmation and result:
                        print(f"No confirmation received within {wait_timeout} seconds for gripper {result}")
                        detector.speech_handler.send_face_command("sad")
                        play_tts("Did not receive confirmation from the gripper.")
                        time.sleep(2) 

            except KeyboardInterrupt:
                print("\nExiting by user request...")
                detector.speech_handler.send_face_command("neutral") 
            except Exception as e:
                print(f"Main loop error: {e}")
                detector.speech_handler.send_face_command("sad") 
                import traceback
                traceback.print_exc()
                time.sleep(1)
                
    finally:
        try:
            detector.speech_handler.send_face_command("neutral")
            time.sleep(0.1)
        except Exception:
            pass
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
