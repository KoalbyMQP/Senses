from pathlib import Path
from typing import Dict, Any
import yaml

from pathlib import Path

class Settings:
    def __init__(self):
        self.settings = {
            'depthai_path': Path('/home/finley/Documents/GitHub/RaspberryPi-Code_24-25/test/io/inputs/camera/oak-d-lite/vdepthai/depthai'),
            'venv_path': Path('/home/finley/Documents/GitHub/RaspberryPi-Code_24-25/test/io/inputs/camera/oak-d-lite/vdepthai'),
            'sampling_interval': 0.1  # seconds
        }

    def get(self, key: str):
        return self.settings.get(key)

    def validate_paths(self):
        """Validate that all required paths exist"""
        if not self.settings['depthai_path'].exists():
            raise FileNotFoundError(f"DepthAI path does not exist: {self.settings['depthai_path']}")
            
        venv_activate = self.settings['venv_path'] / 'bin' / 'activate'
        if not venv_activate.exists():
            # Try alternate path
            alt_venv_path = Path(str(self.settings['venv_path']).replace('/oak-d-lite/', '/oak-d-lite/vdepthai/'))
            alt_venv_activate = alt_venv_path / 'bin' / 'activate'
            if alt_venv_activate.exists():
                self.settings['venv_path'] = alt_venv_path
            else:
                raise FileNotFoundError(f"Virtual environment not found at {venv_activate} or {alt_venv_activate}")