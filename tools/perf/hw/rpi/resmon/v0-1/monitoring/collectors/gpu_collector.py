import subprocess
from typing import Dict, Any

class GPUCollector:
    @staticmethod
    def collect() -> Dict[str, Any]:
        gpu_data = {}
        try:
            # pi 4 and 5 
            gpu_data.update(GPUCollector._collect_basic_metrics())
            
            # Pi 5 specific 
            if GPUCollector._is_pi5():
                gpu_data.update(GPUCollector._collect_pi5_metrics())
                
        except Exception as e:
            gpu_data = {'gpu_memory': 0, 'gpu_temp': 0, 'gpu_freq': 0}
            
        return gpu_data
    
    @staticmethod
    def _is_pi5() -> bool:
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Model'):
                        return 'Raspberry Pi 5' in line
            return False
        except:
            return False
    
    @staticmethod
    def _collect_basic_metrics() -> Dict[str, Any]:
        metrics = {}
        try:
            # GPU Memory
            mem_output = subprocess.check_output(['vcgencmd', 'get_mem', 'gpu']).decode()
            metrics['gpu_memory'] = int(mem_output.replace('gpu=', '').replace('M', ''))
            
            # GPU Temperature
            temp_output = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
            metrics['gpu_temp'] = float(temp_output.replace('temp=', '').replace('\'C', ''))
            
            # GPU Frequency
            freq_output = subprocess.check_output(['vcgencmd', 'measure_clock', 'core']).decode()
            metrics['gpu_freq'] = int(freq_output.split('=')[1]) / 1000000  # using Mhz
        except:
            pass
        return metrics
    
    @staticmethod
    def _collect_pi5_metrics() -> Dict[str, Any]:
        pi5_metrics = {}
        try:
            # VideoCore VII specific metrics
            pi5_metrics['gpu_busy'] = GPUCollector._get_gpu_load()
            
            # Power state
            power_output = subprocess.check_output(['vcgencmd', 'get_throttled']).decode()
            pi5_metrics['power_state'] = int(power_output.split('=')[1], 16)
            
        except:
            pass
        return pi5_metrics
    
    @staticmethod
    def _get_gpu_load() -> float:
        try:
            output = subprocess.check_output(['vcgencmd', 'get_lcd_info']).decode()
            # Parse GPU busy percentage from output
            return float(output.split(',')[2]) if len(output.split(',')) > 2 else 0.0
        except:
            return 0.0
