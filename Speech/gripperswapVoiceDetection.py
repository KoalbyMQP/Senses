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
        self.previous_gripper = None
        self.confirm_context = zmq.Context()
        self.confirm_socket = self.confirm_context.socket(zmq.SUB)
        self.confirm_socket.connect("tcp://localhost:5562")
        self.confirm_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
    def listen_and_process(self):
        try:
            with sr.Microphone() as src:
                r = sr.Recognizer()
                r.adjust_for_ambient_noise(src, duration=0.2)
                print("Listening for swap commands...")
                
                try:
                    audio = r.listen(src, timeout=3, phrase_time_limit=3)
                except sr.WaitTimeoutError:
                    print("Audio capture timeout - no speech detected")
                    return None
                
                print("Processing audio...")
                try:
                    text = r.recognize_google(audio).lower()
                    print(f"Recognized: {text}")
                except sr.UnknownValueError:
                    print("Could not understand audio")
                    return None
                except sr.RequestError as e:
                    print(f"Google API error: {e}")
                    return None
                
                print(f"Raw text: '{text}'")
                if "swap gripper" in text:
                    try:
                        parts = text.split("swap gripper")
                        print(f"Split parts: {parts}")
                        gripper_num = int(parts[1].strip())
                        print(f"Parsed number: {gripper_num}")
                        
                        if 1 <= gripper_num <= 10:
                            self.speech_handler.send_command(gripper_num)
                            self.previous_gripper = self.previous_gripper if self.previous_gripper else gripper_num
                            return gripper_num
                        else:
                            print("Number out of valid range (1-10)")
                    except (ValueError, IndexError) as e:
                        print(f"Number parsing error: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("Keyword not detected in text")
                return None
                
        except Exception as e:
            print(f"Critical error in audio processing: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def listen_for_confirmation(self):
        try:
            return self.confirm_socket.recv_string(flags=zmq.NOBLOCK)
        except zmq.Again:
            return None

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

def run_gripper_swap_detection():
    detector = SpeechDetector()
    try:
        pygame.init()
        pygame.mixer.init()
        
        play_tts("Gripper swap system ready. Say 'swap gripper' followed by a number 1 through 10.")
        
        while True:
            try:
                result = detector.listen_and_process()
                confirmation = None
                start_time = time.time()
                while time.time() - start_time < 5:  # Wait for confirmation
                    confirmation = detector.listen_for_confirmation()
                    if confirmation:
                        parts = confirmation.split('|')
                        if parts[-1] == "success":
                            play_tts(f"Swap to {parts[0]} successful")
                        elif parts[-1] == "already_active":
                            play_tts(f"Gripper {parts[0]} already active")
                        break
                    time.sleep(0.1)
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

def play_tts(text):
    try:
        tts = gTTS(text=text, lang='en')
        temp_file = f"temp_{time.time()}.mp3"
        tts.save(temp_file)
        
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        
        start_time = time.time()
        while pygame.mixer.music.get_busy():
            if time.time() - start_time > 5:
                print("Audio playback timeout")
                break
            pygame.time.Clock().tick(10)
            
    except Exception as e:
        print(f"TTS Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as e:
                print(f"Error cleaning up audio file: {e}")

if __name__ == "__main__":
    try:
        run_gripper_swap_detection()
    except Exception as e:
        print(f"\n!!! VOICE DETECTION CRASHED: {str(e)} !!!")
        import traceback
        traceback.print_exc()
        input("Press Enter to close this error window...")
