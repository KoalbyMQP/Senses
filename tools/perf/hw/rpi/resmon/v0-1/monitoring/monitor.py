import time
import signal
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import pandas as pd
import os

from .collectors.cpu_collector import CPUCollector
from .collectors.memory_collector import MemoryCollector
from .collectors.gpu_collector import GPUCollector
from .collectors.system_collector import SystemCollector
from .utils.csv_handler import CSVHandler
from .utils.plotting import Plotter
from .utils.logger import Logger
from .utils.markdown_handler import MarkdownHandler
from .utils.latex_handler import LaTeXHandler
from .config.settings import Settings

class Monitor:
    def __init__(self):
        self.settings = Settings()
        self.depthai_process = None
        self.should_stop = False
        self.monitoring_thread = None
        self._in_post_run = False
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        if not self._in_post_run:
            self.should_stop = True
            if self.depthai_process:
                self.depthai_process.terminate()

    def collect_metrics(self) -> dict:
        metrics = {}
        metrics.update(CPUCollector.collect())
        metrics.update(MemoryCollector.collect())
        metrics.update(GPUCollector.collect())
        metrics.update(SystemCollector.collect())
        metrics['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return metrics
    
    def _prepare_metrics_data(self, log_dir: Path) -> List[Dict]:
        metrics_data = []
        for phase in ['prerun', 'runtime', 'postrun']:
            df = pd.read_csv(log_dir / phase / 'metrics.csv')
            for column in df.columns:
                if column != 'timestamp':
                    metrics_data.append({
                        'name': column,
                        'plot_path': str(log_dir / 'summary' / f'{column}_plot.png'),
                        'mean': f"{df[column].mean():.2f}",
                        'max': f"{df[column].max():.2f}",
                        'min': f"{df[column].min():.2f}"
                    })
        return metrics_data
    
    def _generate_analysis(self, log_dir: Path) -> str:
        runtime_df = pd.read_csv(log_dir / 'runtime' / 'metrics.csv')
        analysis = []
        
        # CPU Analysis
        cpu_load = runtime_df['cpu_percent'].mean()
        if cpu_load > 80:
            analysis.append("High CPU utilization detected")
        
        # Memory Analysis
        mem_usage = runtime_df['ram_percent'].mean()
        if mem_usage > 85:
            analysis.append("Memory usage is approaching system limits")
        
        # Temperature Analysis
        cpu_temp = runtime_df['cpu_temp'].max()
        if cpu_temp > 80:
            analysis.append("CPU temperature reached concerning levels")
            
        return "\n".join(analysis) if analysis else "System performed within normal parameters"
    
    def monitor_phase(self, phase: str, duration: Optional[int], csv_handler: CSVHandler):
        start_time = time.time()
        last_metric_time = start_time
        
        while True:
            try:
                current_time = time.time()
                
                # Check DepthAI process status for runtime phase
                if phase == "runtime":
                    if self.depthai_process and self.depthai_process.poll() is not None:
                        Logger.logger.info("DepthAI process ended")
                        break
                
                    if self.should_stop:
                        break
                
                # Collect metrics at regular intervals
                if current_time - last_metric_time >= self.settings.get('sampling_interval'):
                    metrics = self.collect_metrics()
                    csv_handler.write_row(metrics)
                    last_metric_time = current_time
                
                # Check duration for timed phases
                if duration and (current_time - start_time) >= duration:
                    break
                
                # Small sleep to prevent CPU hogging
                time.sleep(0.001)
                
            except KeyboardInterrupt:
                if phase != "postrun":
                    self.should_stop = True
                break
            except Exception as e:
                Logger.logger.error(f"Error in {phase} monitoring: {str(e)}")
                if phase == "runtime":
                    self.should_stop = True
                    break
    
    def _start_depthai(self):
        try:
            env = dict(subprocess.os.environ)
            depthai_path = self.settings.get('depthai_path')
            venv_path = self.settings.get('venv_path')
            
            self.settings.validate_paths()
            
            venv_activate = str(venv_path / 'bin' / 'activate')
            if not Path(venv_activate).exists():
                venv_path = Path(str(venv_path).replace('/oak-d-lite/', '/oak-d-lite/vdepthai/'))
                venv_activate = str(venv_path / 'bin' / 'activate')
                
            if not Path(venv_activate).exists():
                raise FileNotFoundError(f"Virtual environment activation script not found at {venv_activate}")
            
            activate_cmd = f'source {venv_activate} && '
            cmd = f"{activate_cmd} cd {depthai_path} && python3 depthai_demo.py"
            
            Logger.logger.info(f"Starting DepthAI from: {depthai_path}")
            Logger.logger.info(f"Using virtual environment: {venv_path}")
            
            self.depthai_process = subprocess.Popen(
                cmd,
                shell=True,
                executable='/bin/bash',
                preexec_fn=os.setsid,  
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except Exception as e:
            Logger.logger.error(f"Failed to start DepthAI: {str(e)}")
            raise
    
    def run(self, pre_duration: int = 30, post_duration: int = 30, output_dir: Optional[str] = None):
        start_time = time.time()
        
        timestamp = datetime.now().strftime('%m%d%Y_%H%M%S')
        log_dir = Path(output_dir) if output_dir else Path.cwd() / f'logs_{timestamp}'
        for subdir in ['prerun', 'runtime', 'postrun', 'summary']:
            (log_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        Logger.setup(log_dir)
        Logger.logger.info("Starting DepthAI monitoring session")
        
        try:
            # Pre-run phase
            Logger.logger.info(f"Starting pre-run monitoring ({pre_duration}s)")
            prerun_csv = CSVHandler(log_dir / 'prerun' / 'metrics.csv')
            self.monitor_phase('prerun', pre_duration, prerun_csv)

            # Runtime phase
            Logger.logger.info("Starting DepthAI")
            self._start_depthai()
            runtime_csv = CSVHandler(log_dir / 'runtime' / 'metrics.csv')
            self.monitor_phase('runtime', None, runtime_csv)

            # Ensure clean process termination
            if self.depthai_process and self.depthai_process.poll() is None:
                os.killpg(os.getpgid(self.depthai_process.pid), signal.SIGKILL)
                self.depthai_process = None

            # Post-run phase - start immediately after runtime
            Logger.logger.info(f"Starting post-run monitoring ({post_duration}s)")
            self._in_post_run = True
            self.should_stop = False  
            postrun_csv = CSVHandler(log_dir / 'postrun' / 'metrics.csv')
            Logger.logger.debug(f"Starting post-run at {time.time()}")
            self.monitor_phase('postrun', post_duration, postrun_csv)
            Logger.logger.debug(f"Finished post-run at {time.time()}")
    
            Logger.logger.info("Generating reports")
            
            Plotter.create_summary_plots(
                log_dir / 'prerun' / 'metrics.csv',
                log_dir / 'runtime' / 'metrics.csv',
                log_dir / 'postrun' / 'metrics.csv',
                log_dir / 'summary'
            )
            
            md_handler = MarkdownHandler()
            for phase in ['prerun', 'runtime', 'postrun']:
                csv_path = log_dir / phase / 'metrics.csv'
                md_path = log_dir / phase / 'report.md'
                md_handler.create_phase_report(csv_path, md_path)
            
            latex_handler = LaTeXHandler()
            report_data = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'duration': time.time() - start_time,
                'pre_duration': pre_duration,
                'post_duration': post_duration,
                'metrics': self._prepare_metrics_data(log_dir),
                'analysis': self._generate_analysis(log_dir)
            }
            latex_handler.generate_pdf(report_data, log_dir / 'summary' / 'report')
            
            Logger.logger.info(f"Monitoring session completed. Reports available in: {log_dir}")
            
        except Exception as e:
            Logger.logger.error(f"Error during monitoring: {str(e)}")
            self.should_stop = True
        finally:
            self._in_post_run = False
            if self.depthai_process and self.depthai_process.poll() is None:
                os.killpg(os.getpgid(self.depthai_process.pid), signal.SIGKILL)