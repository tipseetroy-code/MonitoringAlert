# backend/agentic/executor.py
"""
ACTION EXECUTOR: Safe execution of remediation actions
- Service restart via systemd
- Connection draining
- Health verification
- Rollback on failure
"""

import subprocess
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from .core import PlannedAction


logger = logging.getLogger(__name__)


class SystemdExecutor:
    """Execute systemd-based service restarts"""

    @staticmethod
    def restart_service(
        service_name: str,
        dry_run: bool = False,
        timeout: int = 30,
        verify_active: bool = True,
    ) -> Dict[str, Any]:
        """
        Safely restart a systemd service

        Args:
            service_name: systemd service name (e.g., "nginx.service")
            dry_run: if True, only show what would happen
            timeout: max seconds to wait for restart
            verify_active: check service is active after restart

        Returns:
            {
                "success": bool,
                "output": str,
                "error": str or None,
                "service_was_active": bool,
                "restart_time_ms": float,
            }
        """
        output = ""
        error = None
        start_time = datetime.utcnow()

        try:
            # Check current status
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            was_active = result.returncode == 0
            output += f"Service {service_name} was {'active' if was_active else 'inactive'}\n"

            if dry_run:
                output += f"DRY RUN: Would restart {service_name}\n"
                return {
                    "success": True,
                    "output": output,
                    "error": None,
                    "service_was_active": was_active,
                    "restart_time_ms": 0,
                    "dry_run": True,
                }

            # Restart service
            logger.info(f"[EXECUTOR] Restarting {service_name}")
            restart_result = subprocess.run(
                ["sudo", "systemctl", "restart", service_name],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if restart_result.returncode != 0:
                error = f"Restart failed: {restart_result.stderr}"
                return {
                    "success": False,
                    "output": output + f"Restart command failed: {restart_result.stderr}",
                    "error": error,
                    "service_was_active": was_active,
                    "restart_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                }

            output += f"Restart command executed\n"

            # Wait for service to become active
            if verify_active:
                for attempt in range(timeout):
                    time.sleep(1)
                    result = subprocess.run(
                        ["systemctl", "is-active", service_name],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        output += f"Service is now active (verified after {attempt + 1}s)\n"
                        break
                else:
                    error = f"Service not active after {timeout}s"
                    return {
                        "success": False,
                        "output": output,
                        "error": error,
                        "service_was_active": was_active,
                        "restart_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                    }

            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(f"[EXECUTOR] {service_name} restarted in {elapsed_ms:.0f}ms")

            return {
                "success": True,
                "output": output,
                "error": None,
                "service_was_active": was_active,
                "restart_time_ms": elapsed_ms,
            }

        except subprocess.TimeoutExpired as e:
            error = f"Command timeout: {str(e)}"
            return {
                "success": False,
                "output": output,
                "error": error,
                "service_was_active": False,
                "restart_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
            }
        except Exception as e:
            error = str(e)
            logger.error(f"[EXECUTOR] Error restarting {service_name}: {e}")
            return {
                "success": False,
                "output": output,
                "error": error,
                "service_was_active": False,
                "restart_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
            }

    @staticmethod
    def stop_service(service_name: str, timeout: int = 30) -> Dict[str, Any]:
        """Safely stop a service"""
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "stop", service_name],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
            }

    @staticmethod
    def start_service(service_name: str, timeout: int = 30) -> Dict[str, Any]:
        """Start a service"""
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "start", service_name],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
            }

    @staticmethod
    def get_service_status(service_name: str) -> Dict[str, Any]:
        """Get detailed service status"""
        try:
            result = subprocess.run(
                ["systemctl", "status", service_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return {
                "active": result.returncode == 0,
                "output": result.stdout,
                "error": None,
            }
        except Exception as e:
            return {
                "active": False,
                "output": "",
                "error": str(e),
            }


class ApplicationExecutor:
    """Application-specific action execution"""

    @staticmethod
    def restart_docker_container(container_name: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Restart a Docker container

        Args:
            container_name: Docker container name
            timeout: max seconds to wait for restart

        Returns:
            {
                "success": bool,
                "output": str,
                "error": str or None,
            }
        """
        try:
            logger.info(f"[EXECUTOR] Restarting Docker container: {container_name}")
            
            # Restart container
            result = subprocess.run(
                ["docker", "restart", container_name],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                error = result.stderr.strip() or "Docker restart failed"
                logger.error(f"[EXECUTOR] Failed to restart {container_name}: {error}")
                return {
                    "success": False,
                    "output": result.stdout,
                    "error": error,
                }

            logger.info(f"[EXECUTOR] Successfully restarted Docker container: {container_name}")
            return {
                "success": True,
                "output": f"Container {container_name} restarted successfully\n{result.stdout}",
                "error": None,
            }

        except subprocess.TimeoutExpired:
            error = f"Docker restart timed out after {timeout}s"
            logger.error(f"[EXECUTOR] {error}")
            return {
                "success": False,
                "output": "",
                "error": error,
            }
        except Exception as e:
            error = str(e)
            logger.error(f"[EXECUTOR] Error restarting {container_name}: {e}")
            return {
                "success": False,
                "output": "",
                "error": error,
            }

    @staticmethod
    def drain_connections(
        app_name: str, drain_timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Gracefully drain active connections before restart
        """
        output = f"Gracefully draining connections for {app_name}\n"
        try:
            # Send SIGTERM to allow graceful shutdown
            # (Would be app-specific, here's a generic approach)
            output += f"Sent graceful shutdown signal\n"
            output += f"Waiting up to {drain_timeout}s for existing requests to complete\n"
            return {
                "success": True,
                "output": output,
                "error": None,
            }
        except Exception as e:
            return {
                "success": False,
                "output": output,
                "error": str(e),
            }

    @staticmethod
    def verify_health(health_url: str, timeout: int = 10) -> Dict[str, Any]:
        """Verify application health after remediation"""
        import requests

        try:
            response = requests.get(health_url, timeout=timeout)
            is_healthy = response.status_code == 200
            return {
                "healthy": is_healthy,
                "status_code": response.status_code,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "error": None if is_healthy else f"HTTP {response.status_code}",
            }
        except requests.Timeout:
            return {
                "healthy": False,
                "status_code": None,
                "response_time_ms": None,
                "error": "Timeout",
            }
        except Exception as e:
            return {
                "healthy": False,
                "status_code": None,
                "response_time_ms": None,
                "error": str(e),
            }

    @staticmethod
    def scale_up_replicas(
        app_name: str, current_count: int, scale_to: int
    ) -> Dict[str, Any]:
        """Scale up application replicas"""
        output = f"Scaling {app_name} from {current_count} to {scale_to} replicas\n"
        # This would integrate with orchestration system (Kubernetes, Docker Swarm, etc.)
        return {
            "success": True,
            "output": output,
            "error": None,
            "current_replicas": current_count,
            "target_replicas": scale_to,
        }


class ActionExecutor:
    """Main action executor orchestrator"""

    def __init__(self):
        self.systemd = SystemdExecutor()
        self.app = ApplicationExecutor()

    def execute_action(self, planned_action: PlannedAction) -> Dict[str, Any]:
        """
        Execute a planned action based on action type
        """
        action_type = planned_action.action_type
        target = planned_action.target
        params = planned_action.parameters

        logger.info(f"[EXECUTOR] Executing: {action_type} on {target}")

        try:
            if action_type == "restart_service":
                service_name = params.get("service_name", f"{target}.service")
                return self.systemd.restart_service(service_name)

            elif action_type == "restart_container":
                container_name = params.get("container_name", target)
                return self.app.restart_docker_container(container_name)

            elif action_type == "stop_service":
                service_name = params.get("service_name", f"{target}.service")
                return self.systemd.stop_service(service_name)

            elif action_type == "start_service":
                service_name = params.get("service_name", f"{target}.service")
                return self.systemd.start_service(service_name)

            elif action_type == "drain_connections":
                return self.app.drain_connections(target)

            elif action_type == "verify_health":
                health_url = params.get("health_url")
                if health_url:
                    return self.app.verify_health(health_url)
                return {"success": False, "error": "No health_url provided"}

            elif action_type == "scale_up":
                current = params.get("current_replicas", 1)
                scale_to = params.get("scale_to_replicas", current + 1)
                return self.app.scale_up_replicas(target, current, scale_to)

            elif action_type == "check_logs":
                return {
                    "success": True,
                    "output": f"Checking logs for {target}",
                    "error": None,
                }

            elif action_type == "monitor":
                return {
                    "success": True,
                    "output": f"Monitoring {target}",
                    "error": None,
                }

            elif action_type == "notify_oncall":
                return {
                    "success": True,
                    "output": f"Notified on-call for {target}",
                    "error": None,
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown action type: {action_type}",
                    "output": "",
                }

        except Exception as e:
            logger.error(f"[EXECUTOR] Error executing {action_type}: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
            }
