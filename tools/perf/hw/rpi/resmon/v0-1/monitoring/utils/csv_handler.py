import csv
from typing import Dict, List
from pathlib import Path

class CSVHandler:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.headers = None
        
    def write_row(self, data: Dict):
        if not self.headers:
            self.headers = list(data.keys())
            with open(self.filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self.headers)
        
        with open(self.filepath, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([data[h] for h in self.headers])