"""
Performance monitoring system for FS Reconciliation Agents.
"""

import time
import psutil
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
import json


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str]


class PerformanceMonitor:
    """Performance monitoring system."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics_store = defaultdict(lambda: deque(maxlen=1000))
        self.alert_thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "response_time": 5.0,
            "error_rate": 5.0
        }
    
    def record_metric(self, name: str, value: float, unit: str, tags: Dict[str, str] = None):
        """Record a performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self.metrics_store[name].append(metric)
        
        # Check threshold
        if name in self.alert_thresholds and value > self.alert_thresholds[name]:
            self.logger.warning(f"Performance threshold exceeded: {name} = {value}")
    
    def get_system_metrics(self):
        """Get current system metrics."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.record_metric("cpu_usage", cpu_percent, "percent")
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.record_metric("memory_usage", memory.percent, "percent")
        self.record_metric("memory_bytes", memory.used, "bytes")
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        self.record_metric("disk_usage", disk_percent, "percent")
        
        return {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_bytes": memory.used,
            "disk_usage": disk_percent
        }
    
    def track_request(self, method: str, endpoint: str, duration: float, status_code: int):
        """Track HTTP request performance."""
        self.record_metric(
            "http_request_duration",
            duration,
            "seconds",
            {"method": method, "endpoint": endpoint, "status": str(status_code)}
        )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        summary = {}
        for metric_name, metrics in self.metrics_store.items():
            if metrics:
                values = [m.value for m in metrics]
                summary[metric_name] = {
                    "current": values[-1],
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
        return summary


# Global instance
performance_monitor = PerformanceMonitor()
