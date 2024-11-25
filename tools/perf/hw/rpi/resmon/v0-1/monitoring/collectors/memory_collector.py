import psutil
from typing import Dict, Any

class MemoryCollector:
    @staticmethod
    def collect() -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            'ram_total': mem.total,
            'ram_used': mem.used,
            'ram_percent': mem.percent,
            'swap_total': swap.total,
            'swap_used': swap.used,
            'swap_percent': swap.percent
        }