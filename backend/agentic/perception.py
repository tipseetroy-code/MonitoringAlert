# backend/agentic/perception.py
"""
PERCEPTION LAYER: Collects health signals from multiple sources
- HTTP health checks
- Application logs
- System metrics (CPU, memory, disk)
- Service status (systemd)
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
import subprocess
import json

from .core import Signal


logger = logging.getLogger(__name__)


class HealthChecker:
    """HTTP-based health checks"""

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    async def check(self, app_name: str, health_url: str) -> Signal:
        """
        Check app health via HTTP endpoint
        Returns:
        - healthy: 200 response, response time < 1s
        - degraded: 200 response, response time 1-5s or partial failure
        - unhealthy: non-200 response or timeout
        - critical: exception during check
        """
        start = datetime.utcnow()
        status = "critical"
        value = None
        error = None

        try:
            response = requests.get(health_url, timeout=self.timeout)
            response_time_ms = (datetime.utcnow() - start).total_seconds() * 1000

            if response.status_code == 200:
                if response_time_ms < 1000:
                    status = "healthy"
                elif response_time_ms < 5000:
                    status = "degraded"
                else:
                    status = "unhealthy"
            else:
                status = "unhealthy"
                error = f"HTTP {response.status_code}"

            value = {
                "response_time_ms": response_time_ms,
                "status_code": response.status_code,
                "body_length": len(response.text),
            }

        except requests.Timeout:
            status = "critical"
            error = "Timeout"
        except Exception as e:
            status = "critical"
            error = str(e)

        return Signal(
            timestamp=datetime.utcnow().isoformat(),
            source="health_check",
            app_name=app_name,
            status=status,
            value=value,
            metadata={"url": health_url, "error": error} if error else {"url": health_url},
        )


class LogAnalyzer:
    """Application log monitoring"""

    def __init__(self, log_file: str):
        self.log_file = log_file

    async def check(self, app_name: str) -> Signal:
        """
        Analyze recent logs for errors
        Looks for ERROR, CRITICAL, exception patterns
        """
        status = "healthy"
        error_count = 0
        recent_errors = []

        try:
            # Read last 100 lines
            with open(self.log_file, "r") as f:
                lines = f.readlines()[-100:]

            for line in lines:
                if any(keyword in line.upper() for keyword in ["ERROR", "CRITICAL", "EXCEPTION"]):
                    error_count += 1
                    recent_errors.append(line.strip())

            if error_count > 10:
                status = "critical"
            elif error_count > 5:
                status = "unhealthy"
            elif error_count > 0:
                status = "degraded"

        except FileNotFoundError:
            status = "critical"
            recent_errors = ["Log file not found"]
        except Exception as e:
            status = "unhealthy"
            recent_errors = [str(e)]

        return Signal(
            timestamp=datetime.utcnow().isoformat(),
            source="log",
            app_name=app_name,
            status=status,
            value={
                "error_count": error_count,
                "recent_errors": recent_errors[-5:],
            },
            metadata={"log_file": self.log_file},
        )


class MetricsCollector:
    """System metrics collection"""

    async def check_cpu(self, app_name: str) -> Signal:
        """CPU usage signal"""
        try:
            # Simplified: get CPU % (platform-dependent)
            cpu_percent = self._get_cpu_percent()

            if cpu_percent > 90:
                status = "critical"
            elif cpu_percent > 75:
                status = "unhealthy"
            elif cpu_percent > 50:
                status = "degraded"
            else:
                status = "healthy"

            return Signal(
                timestamp=datetime.utcnow().isoformat(),
                source="metric",
                app_name=app_name,
                status=status,
                value={"cpu_percent": cpu_percent},
                metadata={"metric_type": "cpu"},
            )
        except Exception as e:
            logger.warning(f"CPU check failed: {e}")
            return Signal(
                timestamp=datetime.utcnow().isoformat(),
                source="metric",
                app_name=app_name,
                status="unhealthy",
                value=None,
                metadata={"metric_type": "cpu", "error": str(e)},
            )

    async def check_memory(self, app_name: str) -> Signal:
        """Memory usage signal"""
        try:
            mem_percent = self._get_memory_percent()

            if mem_percent > 90:
                status = "critical"
            elif mem_percent > 80:
                status = "unhealthy"
            elif mem_percent > 60:
                status = "degraded"
            else:
                status = "healthy"

            return Signal(
                timestamp=datetime.utcnow().isoformat(),
                source="metric",
                app_name=app_name,
                status=status,
                value={"memory_percent": mem_percent},
                metadata={"metric_type": "memory"},
            )
        except Exception as e:
            logger.warning(f"Memory check failed: {e}")
            return Signal(
                timestamp=datetime.utcnow().isoformat(),
                source="metric",
                app_name=app_name,
                status="unhealthy",
                value=None,
                metadata={"metric_type": "memory", "error": str(e)},
            )

    async def check_disk(self, app_name: str, path: str = "/") -> Signal:
        """Disk usage signal"""
        try:
            disk_percent = self._get_disk_percent(path)

            if disk_percent > 90:
                status = "critical"
            elif disk_percent > 85:
                status = "unhealthy"
            elif disk_percent > 70:
                status = "degraded"
            else:
                status = "healthy"

            return Signal(
                timestamp=datetime.utcnow().isoformat(),
                source="metric",
                app_name=app_name,
                status=status,
                value={"disk_percent": disk_percent},
                metadata={"metric_type": "disk", "path": path},
            )
        except Exception as e:
            logger.warning(f"Disk check failed: {e}")
            return Signal(
                timestamp=datetime.utcnow().isoformat(),
                source="metric",
                app_name=app_name,
                status="unhealthy",
                value=None,
                metadata={"metric_type": "disk", "error": str(e)},
            )

    def _get_cpu_percent(self) -> float:
        """Get CPU usage percentage"""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except ImportError:
            # Fallback for Linux without psutil
            try:
                result = subprocess.run(
                    "grep -c ^processor /proc/cpuinfo | xargs echo",
                    shell=True,
                    capture_output=True,
                    text=True,
                )
                return float(result.stdout.strip()) * 10  # Mock
            except:
                return 50.0

    def _get_memory_percent(self) -> float:
        """Get memory usage percentage"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            try:
                result = subprocess.run(
                    "free | grep Mem | awk '{print ($3/$2) * 100}'",
                    shell=True,
                    capture_output=True,
                    text=True,
                )
                return float(result.stdout.strip())
            except:
                return 50.0

    def _get_disk_percent(self, path: str) -> float:
        """Get disk usage percentage"""
        try:
            import psutil
            return psutil.disk_usage(path).percent
        except ImportError:
            try:
                result = subprocess.run(
                    f"df {path} | tail -1 | awk '{{print $5}}' | sed 's/%//'",
                    shell=True,
                    capture_output=True,
                    text=True,
                )
                return float(result.stdout.strip())
            except:
                return 50.0


class SystemdMonitor:
    """Monitor systemd service health"""

    async def check_service(self, app_name: str, service_name: str) -> Signal:
        """
        Check systemd service status
        Returns: active/inactive
        """
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5,
            )

            is_active = result.returncode == 0
            status = "healthy" if is_active else "unhealthy"

            return Signal(
                timestamp=datetime.utcnow().isoformat(),
                source="systemd",
                app_name=app_name,
                status=status,
                value={
                    "service": service_name,
                    "active": is_active,
                    "output": result.stdout.strip(),
                },
                metadata={"service": service_name},
            )

        except subprocess.TimeoutExpired:
            return Signal(
                timestamp=datetime.utcnow().isoformat(),
                source="systemd",
                app_name=app_name,
                status="critical",
                value=None,
                metadata={"service": service_name, "error": "Timeout"},
            )
        except Exception as e:
            logger.warning(f"Systemd check failed for {service_name}: {e}")
            return Signal(
                timestamp=datetime.utcnow().isoformat(),
                source="systemd",
                app_name=app_name,
                status="critical",
                value=None,
                metadata={"service": service_name, "error": str(e)},
            )


class PerceptionEngine:
    """Orchestrates all perception sources"""

    def __init__(self, apps_config: List[Dict[str, Any]]):
        """
        apps_config format:
        [
            {
                "name": "api-server",
                "health_url": "http://localhost:8000/health",
                "log_file": "/var/log/api-server.log",
                "systemd_service": "api-server.service"
            }
        ]
        """
        self.apps_config = apps_config
        self.health_checker = HealthChecker()
        self.metrics_collector = MetricsCollector()
        self.systemd_monitor = SystemdMonitor()

    async def collect_signals(self) -> List[Signal]:
        """Collect all signals from all sources"""
        signals = []

        for app_config in self.apps_config:
            app_name = app_config.get("name")
            docker_container = app_config.get("docker_container")

            # Health check
            if "health_url" in app_config:
                signal = await self.health_checker.check(app_name, app_config["health_url"])
                # Add docker_container to metadata if present
                if docker_container:
                    signal.metadata["docker_container"] = docker_container
                signals.append(signal)

            # System metrics
            signals.append(await self.metrics_collector.check_cpu(app_name))
            signals.append(await self.metrics_collector.check_memory(app_name))
            signals.append(await self.metrics_collector.check_disk(app_name))

            # Systemd service
            if "systemd_service" in app_config:
                signal = await self.systemd_monitor.check_service(
                    app_name, app_config["systemd_service"]
                )
                signals.append(signal)

        logger.info(f"[PERCEPTION] Collected {len(signals)} signals from {len(self.apps_config)} apps")
        return signals

    async def monitor_continuously(self, interval_seconds: int = 30, callback=None):
        """
        Continuously monitor and call callback with signals
        Used for real-time agentic loop
        """
        while True:
            try:
                signals = await self.collect_signals()
                if callback:
                    await callback(signals)
            except Exception as e:
                logger.error(f"Error in continuous monitoring: {e}")
            await asyncio.sleep(interval_seconds)
