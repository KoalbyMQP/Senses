import os
from dotenv import load_dotenv
import speech_recognition as sr
import pygame
from gtts import gTTS
import zmq
import time
import whisper
import requests

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
        self.whisper_model = self._load_whisper_model()
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.audit_prompt = """Analyze this command for a robotic gripper swap system. 
        Validate if it contains a gripper swap request between 1-10. Consider:
        1. Direct commands ("Swap to gripper 5")
        2. Implicit requests ("Change to number seven")
        3. Error correction ("I meant gripper three")
        4. Language translation (original may be non-English)
        
        Respond ONLY with the number (1-10) if valid, or 'invalid' otherwise."""
        
    def _load_whisper_model(self):
        try:
            return whisper.load_model("turbo")
        except Exception as e:
            print(f"Whisper load failed: {e}. Using Google fallback")
            return None

    def _transcribe_with_whisper(self, audio_path):
        try:
            if not self.whisper_model:
                return None
                
            audio = whisper.load_audio(audio_path)
            audio = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(audio).to(self.whisper_model.device)
            
            options = whisper.DecodingOptions(task="translate")
            result = whisper.decode(self.whisper_model, mel, options)
            return result.text.lower()
        except Exception as e:
            print(f"Whisper error: {e}")
            return None

    def _audit_with_openrouter(self, text):
        if not self.openrouter_api_key:
            return text
            
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "HTTP-Referer": "http://localhost/",
                    "X-Title": "GripperSwapSystem"
                },
                json={
                    "model": "anthropic/claude-3-5-sonnet",
                    "messages": [
                        {"role": "system", "content": self.audit_prompt},
                        {"role": "user", "content": text}
                    ],
                    "temperature": 0.1
                },
                timeout=3
            )
            
            audited_text = response.json()['choices'][0]['message']['content'].strip()
            return audited_text if audited_text.isdigit() and 1 <= int(audited_text) <= 10 else "invalid"
        except Exception as e:
            print(f"Audit error: {e}")
            return text

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
                
                temp_audio = f"temp_audio_{time.time()}.wav"
                with open(temp_audio, "wb") as f:
                    f.write(audio.get_wav_data())

                text = None
                if self.whisper_model:
                    text = self._transcribe_with_whisper(temp_audio)
                
                if not text:
                    try:
                        text = r.recognize_google(audio).lower()
                    except (sr.UnknownValueError, sr.RequestError):
                        pass

                if os.path.exists(temp_audio):
                    os.remove(temp_audio)

                if not text:
                    print("No speech detected")
                    return None

                audited_text = self._audit_with_openrouter(text)
                print(f"Processed text: {text} | Audited: {audited_text}")

                if audited_text.isdigit():
                    gripper_num = int(audited_text)
                else:
                    if "swap gripper" in text:
                        parts = text.split("swap gripper")
                        gripper_num = parts[-1].strip()
                    else:
                        return None

                try:
                    gripper_num = int(gripper_num)
                    if 1 <= gripper_num <= 10:
                        self.speech_handler.send_command(gripper_num)
                        self.previous_gripper = self.previous_gripper if self.previous_gripper else gripper_num
                        return gripper_num
                    else:
                        print("Number out of range")
                except (ValueError, IndexError) as e:
                    print(f"Number parsing error: {e}")
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
