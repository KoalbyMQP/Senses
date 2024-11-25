import multiprocessing
from pickAndPlaceVoiceDetection import listen_and_process
from depthai_handler import DepthAIHandler

if __name__ == "__main__":
    # Start speech detection process
    speech_process = multiprocessing.Process(target=listen_and_process)
    speech_process.start()
    
    # Start DepthAI handler
    depthai_handler = DepthAIHandler()
    depthai_handler.create_pipeline()
    depthai_handler.run()
    
    speech_process.join()
