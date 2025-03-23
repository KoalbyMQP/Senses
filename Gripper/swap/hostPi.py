import zmq
import time
import subprocess
import os
import signal
import socket
import sounddevice

class HostPi:
    def __init__(self):
        self.context = zmq.Context()
        
        self.venv_path = self._get_venv_path()
        
        self.host_ip = self._get_host_ip()
        print(f"\n=== Host Pi IP: {self.host_ip} ===")
        print("Use this IP when starting the client Pi\n")
        
        print(f"\n===== GRIPPER SWAP SYSTEM =====")
        print("Available Gripper IDs:")
        print("1: Default hand")
        print("2: Scoop gripper")
        print("3: Vitals gripper")
        print("4: Thermometer gripper")
        print("5: Board game gripper")
        print("6: Main gripper")
        print("7: Type 2 gripper")
        print("8: Type 3 gripper")
        print("9: Type 4 gripper")
        print("10: Type 5 gripper")
        print("=============================\n")

        self.connected = self._check_internet()
        if not self.connected:
            warning = "No internet connection detected. Please connect to the internet."
            print(warning)
            self._play_tts_offline(warning)
            self.command_receiver = None
            self.client_publisher = None
            self.voice_process = None
            self.confirmation_process = None
        else:
            self.command_receiver = self.context.socket(zmq.SUB)
            self.command_receiver.bind("tcp://*:5560")
            self.command_receiver.setsockopt_string(zmq.SUBSCRIBE, "")
            
            self.client_publisher = self.context.socket(zmq.PUB)
            self.client_publisher.bind("tcp://*:5561")
            
            self.voice_process = self._start_voice_detection()
            self.confirmation_process = self._start_confirmation_listener()

        self.error_occurred = False

    def _check_internet(self, host="8.8.8.8", port=53, timeout=3):
        """Check internet connectivity by trying to connect to a known host (Google DNS)"""
        try:
            socket.setdefaulttimeout(timeout)
            with socket.create_connection((host, port), timeout=timeout) as s:
                return True
        except Exception:
            return False

    def _play_tts_offline(self, message):
        """Play TTS message offline using espeak."""
        try:
            subprocess.Popen(["espeak", message])
        except Exception as e:
            print(f"Failed to play TTS using espeak: {e}")

    def _get_venv_path(self):
        """Get the currently activated virtual environment path or use default"""
        active_venv = os.environ.get('VIRTUAL_ENV')
        if active_venv:
            print(f"Using active virtual environment: {active_venv}")
            return active_venv
        
        # Fallback to hardcoded path 
        fallback_path = "/home/finley/Documents/GitHub/Senses/myvirtual"
        print(f"No active virtual environment detected. Using default: {fallback_path}")
        return fallback_path

    def _start_voice_detection(self):
        """Start voice detection with error handling"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        voice_script = os.path.join(current_dir, "..", "..", "Speech", "detection", "gripperswapVoiceDetection.py")
        venv_path = self.venv_path
        print(f"Current directory: {current_dir}")
        print(f"Voice script: {voice_script}")
        print(f"Venv path: {venv_path}")

        temp_script = "/tmp/gripperVoiceListener.sh"
        with open(temp_script, "w") as f:
            f.write(f"""#!/bin/bash
source "{venv_path}/bin/activate"
export PYTHONPATH="/home/finley/Documents/GitHub/Senses:$PYTHONPATH"
cd {os.path.dirname(voice_script)}
python3 {os.path.basename(voice_script)} || read -p "Error occurred! Press Enter to close..."
""")
        os.chmod(temp_script, 0o755)

        print("\nStarting voice detection interface...")
        return subprocess.Popen(
            f"lxterminal --geometry=80x24 -e 'bash -c \"{temp_script}; exec bash\"'",
            shell=True,
            preexec_fn=os.setsid
        )

    def _start_confirmation_listener(self):
        """Start confirmation listener in new terminal"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        listener_script = os.path.join(current_dir, "confirmationListener.py")
        venv_path = self.venv_path
        
        temp_script = "/tmp/confirmationListener.sh"
        with open(temp_script, "w") as f:
            f.write(f"""#!/bin/bash
source "{venv_path}/bin/activate"
export PYTHONPATH="/home/finley/Documents/GitHub/Senses:$PYTHONPATH"
cd {os.path.dirname(listener_script)}
python3 {os.path.basename(listener_script)} {self.host_ip} || read -p "Error occurred! Press Enter to close..."
""")
        os.chmod(temp_script, 0o755)

        print("\nStarting confirmation listener interface...")
        return subprocess.Popen(
            f"lxterminal --geometry=80x24 -e 'bash -c \"{temp_script}; exec bash\"'",
            shell=True,
            preexec_fn=os.setsid
        )

    def _get_host_ip(self):
        """Get the first non-localhost IP address"""
        try:
            ips = subprocess.check_output(['hostname', '-I']).decode().strip().split()
            return ips[0] if ips else '127.0.0.1'
        except:
            return socket.gethostbyname(socket.gethostname())

    def process_commands(self):
        print("\n===== Host Pi started =====")
        print("The system is now listening for voice commands")
        print("Say 'swap gripper' followed by a number 1-10 or gripper name")
        print("For example: 'swap gripper 3' or 'swap to thermometer gripper'")
        print("============================\n")
        
        try:
            while True:  
                try:
                    time.sleep(0.1) 
                    message = self.command_receiver.recv_string(flags=zmq.NOBLOCK)
                    receive_time = time.time()
                    parts = message.split()
                    if len(parts) == 3 and parts[0] == "SWAP":
                        voice_sent = float(parts[2])
                        host_latency = receive_time - voice_sent
                        print(f"Voice->Host latency: {host_latency*1000:.2f}ms")
                        forward_msg = f"{message} {receive_time}"
                        self.client_publisher.send_string(forward_msg)
                        print(f"Forwarded message: {forward_msg}")
                except zmq.Again:
                    time.sleep(0.1)  
                except Exception as e:
                    print(f"Critical error: {str(e)}")
                    break
        finally:
            if hasattr(self, 'voice_process') and self.voice_process:
                os.killpg(os.getpgid(self.voice_process.pid), signal.SIGTERM)
            if hasattr(self, 'confirmation_process') and self.confirmation_process:
                os.killpg(os.getpgid(self.confirmation_process.pid), signal.SIGTERM)
            print("Cleanly terminated all subprocesses")

    def __del__(self):
        if hasattr(self, 'voice_process') and self.voice_process:
            os.killpg(os.getpgid(self.voice_process.pid), signal.SIGTERM)
        if hasattr(self, 'confirmation_process') and self.confirmation_process:
            os.killpg(os.getpgid(self.confirmation_process.pid), signal.SIGTERM)

if __name__ == "__main__":
    host = HostPi()
    if not host.connected:
        while True:
            warning = "No internet connection detected. Please connect to the internet."
            host._play_tts_offline(warning)
            time.sleep(60)
    else:
        host.process_commands()
