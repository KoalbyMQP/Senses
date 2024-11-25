import logging
from pathlib import Path
from datetime import datetime

class Logger:
    logger = None  
    
    @staticmethod
    def setup(log_dir: Path):
        """Set up logging configuration"""
        Logger.logger = logging.getLogger("depthai_monitor")
        Logger.logger.setLevel(logging.INFO)
        
        file_handler = logging.FileHandler(log_dir / 'monitor.log')
        stream_handler = logging.StreamHandler()
        
        log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(log_format)
        stream_handler.setFormatter(log_format)
        
        Logger.logger.addHandler(file_handler)
        Logger.logger.addHandler(stream_handler)