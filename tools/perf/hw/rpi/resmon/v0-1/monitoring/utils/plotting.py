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
        
        for name, df in {'prerun_df': prerun_df, 'runtime_df': runtime_df, 'postrun_df': postrun_df}.items():
            if df.empty:
                Logger.logger.warning(f"No data found for {name} phase")
                continue
        
        for metric_name, config in metrics.items():
            try:
                fig, ax = plt.subplots()
                
                phase_lengths = [len(df) for df in [prerun_df, runtime_df, postrun_df] if not df.empty]
                phase_markers = np.cumsum(phase_lengths)[:-1]  # Exclude the last marker
                
                # Ensure timestamps are continuous
                runtime_start = prerun_df.index[-1] if not prerun_df.empty else 0
                postrun_start = runtime_df.index[-1] + 1 if not runtime_df.empty else runtime_start

                runtime_df.index = range(runtime_start, runtime_start + len(runtime_df))
                postrun_df.index = range(postrun_start, postrun_start + len(postrun_df))

                # Add phase columns
                prerun_df['phase'] = 'Pre-run'
                runtime_df['phase'] = 'Runtime'
                postrun_df['phase'] = 'Post-run'

                # Concatenate with proper handling of empty dataframes
                dfs_to_concat = [df for df in [prerun_df, runtime_df, postrun_df] if not df.empty]
                combined_df = pd.concat(dfs_to_concat)
                
                for col in config['columns']:
                    if col in combined_df.columns:
                        sns.lineplot(data=combined_df, x=combined_df.index, y=col, label=col)
                
                for marker in phase_markers:
                    plt.axvline(x=marker, color='red', linestyle='--', alpha=0.5)
                
                plt.title(config['title'], pad=20)
                plt.xlabel('Time')
                plt.ylabel(config['ylabel'])
                
                phases = ['Pre-run', 'Runtime', 'Post-run']
                active_phases = [phase for i, phase in enumerate(phases) 
                                if not [prerun_df, runtime_df, postrun_df][i].empty]

                for i, phase in enumerate(active_phases):
                    start = 0 if i == 0 else phase_markers[i-1]
                    end = phase_markers[i] if i < len(phase_markers) else len(combined_df)
                    mid = (start + end) / 2
                    plt.text(mid, plt.ylim()[1], phase,
                            horizontalalignment='center', 
                            verticalalignment='bottom',
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                
                plt.tight_layout()
                plt.savefig(output_dir / f'{metric_name.lower().replace(" ", "_")}.png', dpi=300, bbox_inches='tight')
                plt.close()
            except Exception as e:
                print(f"Error creating plot for {metric_name}: {str(e)}")