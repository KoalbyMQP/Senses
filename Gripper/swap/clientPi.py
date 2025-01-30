import zmq
import time
import argparse

class ClientPi:
    def __init__(self, host_ip):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f"tcp://{host_ip}:5561")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")

    def handle_gripper_command(self, command):
        try:
            _, gripper_num = command.split()
            gripper_num = int(gripper_num)
            print(f"Received command to swap to gripper {gripper_num}")
            
            # Add actual swap logic here later
            self._gripper_switch(gripper_num)
            
        except (ValueError, IndexError):
            print("Invalid command format")

    def _gripper_switch(self, num):
        """Switch case for different grippers"""
        print(f"\n--- Performing action for gripper {num} ---")
        {
            1: lambda: print("Activating type 1 gripper"),
            2: lambda: print("Activating type 2 gripper"),
            3: lambda: print("Activating type 3 gripper"),
            4: lambda: print("Activating type 4 gripper"),
            5: lambda: print("Activating type 5 gripper"),
            6: lambda: print("Activating type 6 gripper"),
            7: lambda: print("Activating type 7 gripper"),
            8: lambda: print("Activating type 8 gripper"),
            9: lambda: print("Activating type 9 gripper"),
            10: lambda: print("Activating type 10 gripper"),
        }.get(num, lambda: print("Invalid gripper number"))()

    def start_listening(self):
        print("ClientPi started. Waiting for commands...")
        while True:
            try:
                message = self.socket.recv_string(flags=zmq.NOBLOCK)
                self.handle_gripper_command(message)
            except zmq.Again:
                time.sleep(0.1)
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Client Pi for gripper control')
    parser.add_argument('--host-ip', required=True, help='IP address of the host Pi')
    args = parser.parse_args()
    
    client = ClientPi(args.host_ip)
    client.start_listening()
