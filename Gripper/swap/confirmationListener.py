import zmq
import time

class ConfirmationListener:
    def __init__(self, host_ip):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.bind(f"tcp://*:5562")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        print(f"Confirmation listener started on {host_ip}:5562")
        
    def start_listening(self):
        while True:
            try:
                message = self.socket.recv_string(flags=zmq.NOBLOCK)
                parts = message.split('|')
                if len(parts) == 8:
                    current_gripper, previous_gripper, voice_sent, host_forwarded, \
                    client_received, processing_time, client_sent, status = parts
                    current_gripper = float(current_gripper)
                    previous_gripper = float(previous_gripper)
                    total_latency = client_sent - voice_sent
                    voice_to_host = host_forwarded - voice_sent
                    host_to_client = client_received - host_forwarded
                    processing = processing_time
                    client_to_confirmation = client_sent - (client_received + processing_time)
                    
                    status_msg = {
                        "success": "Swap successful",
                        "already_active": "Gripper already active"
                    }.get(status, "Unknown status")
                    
                    print(f"\n=== Process Breakdown ==="
                          f"\nStatus: {status_msg}"
                          f"\nPrevious Gripper: {int(previous_gripper)}"
                          f"\nCurrent Gripper: {int(current_gripper)}"
                          f"\nTotal: {total_latency*1000:.2f}ms"
                          f"\nVoice->Host: {voice_to_host*1000:.2f}ms"
                          f"\nHost->Client: {host_to_client*1000:.2f}ms"
                          f"\nProcessing: {processing*1000:.2f}ms"
                          f"\nClient->Confirmation: {client_to_confirmation*1000:.2f}ms")
            except zmq.Again:
                time.sleep(0.1)
            except Exception as e:
                print(f"Listener error: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python confirmationListener.py <host_ip>")
        exit(1)
        
    listener = ConfirmationListener(sys.argv[1])
    listener.start_listening() 