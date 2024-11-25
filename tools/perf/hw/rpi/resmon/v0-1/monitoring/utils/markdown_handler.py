import pandas as pd
from pathlib import Path
from datetime import datetime

class MarkdownHandler:
    @staticmethod
    def create_phase_report(csv_path: Path, output_path: Path):
        df = pd.read_csv(csv_path)
        
        with open(output_path, 'w') as f:
            f.write(f"# Monitoring Report - {output_path.parent.name}\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary Statistics\n\n")
            for column in df.columns:
                if column != 'timestamp':
                    f.write(f"### {column}\n")
                    f.write(f"- Mean: {df[column].mean():.2f}\n")
                    f.write(f"- Max: {df[column].max():.2f}\n")
                    f.write(f"- Min: {df[column].min():.2f}\n\n")
            
            # Raw data in table format
            f.write("## Raw Data\n\n")
            f.write(df.to_markdown())