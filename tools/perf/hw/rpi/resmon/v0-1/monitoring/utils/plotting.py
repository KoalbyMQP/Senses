from logging import Logger
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path
import numpy as np

class Plotter:
    @staticmethod
    def create_summary_plots(prerun_path: Path, runtime_path: Path, postrun_path: Path, output_dir: Path):
        """Create summary plots from all phases"""
        try:
            prerun_df = pd.read_csv(prerun_path)
            runtime_df = pd.read_csv(runtime_path)
            postrun_df = pd.read_csv(postrun_path)
            
            Plotter.create_plots(prerun_df, runtime_df, postrun_df, output_dir)
        except Exception as e:
            print(f"Error creating summary plots: {str(e)}")

    @staticmethod
    def create_plots(prerun_df: pd.DataFrame, runtime_df: pd.DataFrame, postrun_df: pd.DataFrame, output_dir: Path):
        """Create individual plots for each metric"""
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = [12, 6]
        
        metrics = {
            'System Temperature': {
                'columns': ['cpu_temp', 'gpu_temp'],
                'title': 'CPU and GPU Temperature Over Time',
                'ylabel': 'Temperature (°C)'
            },
            'Resource Usage': {
                'columns': ['ram_percent', 'swap_percent'],
                'title': 'Memory Usage Over Time',
                'ylabel': 'Usage (%)'
            },
            'CPU Metrics': {
                'columns': ['cpu_percent'],
                'title': 'CPU Usage Over Time',
                'ylabel': 'Usage (%)'
            },
            'Disk Activity': {
                'columns': ['disk_read', 'disk_write'],
                'title': 'Disk I/O Over Time',
                'ylabel': 'Bytes'
            }
        }
        
        for phase_df in ['prerun_df', 'runtime_df', 'postrun_df']:
            if len(phase_df) == 0:
                Logger.logger.warning(f"No data found for {phase_df} phase")
                continue
        
        for metric_name, config in metrics.items():
            try:
                fig, ax = plt.subplots()
                
                phase_lengths = [len(prerun_df), len(runtime_df), len(postrun_df)]
                total_points = sum(phase_lengths)
                phase_markers = np.cumsum(phase_lengths)
                
                prerun_df['phase'] = 'Pre-run'
                runtime_df['phase'] = 'Runtime'
                postrun_df['phase'] = 'Post-run'
                combined_df = pd.concat([prerun_df, runtime_df, postrun_df])
                
                for col in config['columns']:
                    if col in combined_df.columns:
                        sns.lineplot(data=combined_df, x=combined_df.index, y=col, label=col)
                
                for i, marker in enumerate(phase_markers[:-1]):
                    plt.axvline(x=marker, color='red', linestyle='--', alpha=0.5)
                
                plt.title(config['title'], pad=20)
                plt.xlabel('Time')
                plt.ylabel(config['ylabel'])
                
                phases = ['Pre-run', 'Runtime', 'Post-run']
                for i in range(len(phases)):
                    start = 0 if i == 0 else phase_markers[i-1]
                    end = phase_markers[i] if i < len(phase_markers) else total_points
                    mid = (start + end) / 2
                    plt.text(mid, plt.ylim()[1], phases[i], 
                            horizontalalignment='center', verticalalignment='bottom')
                
                plt.tight_layout()
                plt.savefig(output_dir / f'{metric_name.lower().replace(" ", "_")}.png', dpi=300, bbox_inches='tight')
                plt.close()
            except Exception as e:
                print(f"Error creating plot for {metric_name}: {str(e)}")