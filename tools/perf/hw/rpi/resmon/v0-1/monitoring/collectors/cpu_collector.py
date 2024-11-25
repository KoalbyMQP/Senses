import psutil
from typing import Dict, Any

class CPUCollector:
    @staticmethod
    def collect() -> Dict[str, Any]:
        load1, load5, load15 = psutil.getloadavg()
        return {
            'cpu_percent': psutil.cpu_percent(percpu=False),
            'cpu_freq': psutil.cpu_freq().current,
            'cpu_temp': CPUCollector._get_cpu_temp(),
            'load_avg_1min': load1,
            'load_avg_5min': load5,
            'load_avg_15min': load15
        }
    
    @staticmethod
    def _get_cpu_temp() -> float:
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                return float(f.read().strip()) / 1000.0
        except:
            return 0.0