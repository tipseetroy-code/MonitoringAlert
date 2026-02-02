from ..monitors.windows_monitors import disk_usage_pct

def detect_cpu_issue():
    return {
        "metric": "CPU",
        "value": 100,
        "threshold": 95,
        "duration": "300s"
    }

def detect_disk_issue():
    usage = disk_usage_pct("/")
    if usage > 80:  # Example threshold
        return {
            "metric": "Disk",
            "value": usage,
            "threshold": 80,
            "drive": "/"
        }
    return None
