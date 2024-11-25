import psutil
from typing import Dict, Any

class SystemCollector:
    @staticmethod
    def collect() -> Dict[str, Any]:
        disk = psutil.disk_io_counters()
        net = psutil.net_io_counters()
    
        return {
            'disk_read': disk.read_bytes,
            'disk_write': disk.write_bytes,
            'net_sent': net.bytes_sent,
            'net_recv': net.bytes_recv,
            'process_count': len(psutil.pids()),
            'context_switches': psutil.cpu_stats().ctx_switches,
        }