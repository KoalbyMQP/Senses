import zmq
import time
import subprocess
import os
import signal
import socket

class HostPi:
    def __init__(self):
        self.context = zmq.Context()
        
        #receive from voice detection
        self.command_receiver = self.context.socket(zmq.SUB)
        self.command_receiver.bind("tcp://*:5560")
        self.command_receiver.setsockopt_string(zmq.SUBSCRIBE, "")
        
        #send to clientPi
        self.client_publisher = self.context.socket(zmq.PUB)
        self.client_publisher.bind("tcp://*:5561")

        # Start voice detection in new terminal
        self.voice_process = self._start_voice_detection()

        # Get and display IP at startup
        self.host_ip = self._get_host_ip()
        print(f"\n=== Host Pi IP: {self.host_ip} ===")
        print("Use this IP when starting the client Pi\n")

        # Add error tracking
        self.error_occurred = False

    def _start_voice_detection(self):
        """Start voice detection with error handling"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        voice_script = os.path.join(current_dir, "..", "..", "Speech", "gripperswapVoiceDetection.py")
        venv_path = "/home/finley/Documents/GitHub/Senses/myvirtual"
        print(f"Current directory: {current_dir}")
        print(f"Voice script: {voice_script}")
        print(f"Venv path: {venv_path}")

        
        temp_script = "/tmp/gripperVoiceListener.sh"
        with open(temp_script, "w") as f:
            f.write(f"""#!/bin/bash
# Create virtual environment if missing
if [ ! -d "{venv_path}" ]; then
    python3 -m venv "{venv_path}"
fi

# Activate and install requirements
source "{venv_path}/bin/activate"
export PYTHONPATH="/home/finley/Documents/GitHub/Senses:$PYTHONPATH"
cd {os.path.dirname(voice_script)}
python3 {os.path.basename(voice_script)} || read -p "Error occurred! Press Enter to close..."
deactivate
""")
        os.chmod(temp_script, 0o755)

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
        print("HostPi started. Waiting for commands...")
        try:
            while True:
                try:
                    message = self.command_receiver.recv_string(flags=zmq.NOBLOCK)
                    print(f"Received command: {message}")
                    self.client_publisher.send_string(message)
                except zmq.Again:
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Critical error: {str(e)}")
                    self.error_occurred = True
                    break
                    
            if self.error_occurred:
                print("\n!!! Critical error occurred - keeping terminal open for 60 seconds !!!")
                print("Check the voice detection terminal for possible errors")
                time.sleep(60)
        finally:
            if self.voice_process:
                os.killpg(os.getpgid(self.voice_process.pid), signal.SIGTERM)
                
if __name__ == "__main__":
    host = HostPi()
    host.process_commands()
