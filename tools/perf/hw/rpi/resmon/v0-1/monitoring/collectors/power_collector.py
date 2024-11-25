import subprocess
from typing import Dict, Any

class PowerCollector:
    @staticmethod
    def collect() -> Dict[str, Any]:
        if not PowerCollector._is_pi5():
            return {}
            
        power_data = {}
        try:
            power_data['voltage'] = PowerCollector._get_voltage()
            power_data['current'] = PowerCollector._get_current()
            power_data['power_state'] = PowerCollector._get_power_state()
        except:
            power_data = {'voltage': 0, 'current': 0, 'power_state': 'unknown'}
            
        return power_data
    
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
    def _get_voltage() -> float:
        try:
            output = subprocess.check_output(['vcgencmd', 'measure_volts', 'core']).decode()
            return float(output.replace('volt=', '').replace('V', ''))
        except:
            return 0.0
    
    @staticmethod
    def _get_current() -> float:
        try:
            output = subprocess.check_output(['vcgencmd', 'measure_current']).decode()
            return float(output.replace('current=', '').replace('mA', ''))
        except:
            return 0.0
    
    @staticmethod
    def _get_power_state() -> str:
        try:
            output = subprocess.check_output(['vcgencmd', 'get_throttled']).decode()
            state = int(output.split('=')[1], 16)
            
            states = []
            if state & 0x1:
                states.append('Under-voltage')
            if state & 0x2:
                states.append('Frequency capped')
            if state & 0x4:
                states.append('Throttled')
            
            return ', '.join(states) if states else 'Normal'
        except:
            return 'unknown'