# backend/api/autonomous_agent_service.py
"""
🤖 Autonomous Agent Service - Continuous Monitoring & Autonomous Action
Agents run 24/7 in background, detect issues, make decisions, take autonomous actions
"""

import asyncio
import json
import logging
import os
import subprocess
import csv
import re
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import threading
import time
from google import genai
from groq import Groq
import requests

logger = logging.getLogger(__name__)

# Initialize API clients
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ============== Helper Functions ==============
def call_groq_llm(prompt: str, model: str = "llama-3.3-70b-versatile") -> str:
    """Call Groq API for LLM inference (fast and high quota)"""
    try:
        response = groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API error: {str(e)}")
        return "{}"

def extract_json_from_response(text: str) -> Dict:
    """Extract JSON from Gemini response (handles markdown wrapping)"""
    if not text:
        return {}
    
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract from markdown code blocks
    import re
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find any JSON object in the text
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    logger.warning(f"Could not parse JSON from response: {text[:100]}")
    return {}

# ============== Agent Decision Models ==============
class ActionType(Enum):
    """Types of autonomous actions agents can take"""
    RENEW_CERTIFICATE = "renew_certificate"
    PATCH_VULNERABILITY = "patch_vulnerability"
    RESTART_SERVICE = "restart_service"
    SCALE_RESOURCE = "scale_resource"
    CREATE_JIRA = "create_jira"
    SEND_NOTIFICATION = "send_notification"
    EXECUTE_RUNBOOK = "execute_runbook"
    QUARANTINE = "quarantine"

class AgentDecision:
    """Autonomous agent decision"""
    def __init__(self, agent_name: str, decision: str, action: ActionType, 
                 confidence: float, context: Dict):
        self.agent_name = agent_name
        self.decision = decision  # "approve", "defer", "escalate"
        self.action = action
        self.confidence = confidence  # 0-1
        self.context = context
        self.timestamp = datetime.now()
        self.executed = False
        self.result = None

# ============== Autonomous Agents ==============

class SSLCertificateAgent:
    """Agent: Autonomous SSL Certificate Management"""
    
    def __init__(self, client: genai.Client, model: str = "models/gemini-2.5-flash"):
        self.client = client
        self.model = model
        self.name = "SSL Certificate Agent"
        self.last_run = None
        self.certificates = {}
        
    async def monitor(self):
        """Continuously monitor SSL certificates"""
        while True:
            try:
                # Fetch certs from Venefi/Let's Encrypt/Portal
                certs = await self._fetch_certificates()
                
                for cert in certs:
                    decision = await self._analyze_certificate(cert)
                    
                    if decision and decision.confidence > 0.7:  # Autonomous threshold
                        await self._execute_decision(decision)
                        
                self.last_run = datetime.now()
            except Exception as e:
                logger.error(f"❌ {self.name} error: {str(e)}")
            
            # Run every 1 hour
            await asyncio.sleep(3600)
    
    async def _fetch_certificates(self) -> List[Dict]:
        """Fetch certificates from all sources"""
        # Placeholder: would call Venefi API, Let's Encrypt, Portal
        return [
            {"domain": "api.example.com", "expires_in_days": 15, "status": "valid"},
            {"domain": "web.example.com", "expires_in_days": 3, "status": "critical"},
        ]
    
    async def _analyze_certificate(self, cert: Dict) -> Optional[AgentDecision]:
        """Use LLM to analyze certificate and decide action (Groq with Gemini fallback)"""
        prompt = f"""
        Analyze this SSL certificate and decide the action:
        Domain: {cert['domain']}
        Days until expiry: {cert['expires_in_days']}
        Status: {cert['status']}
        
        Respond with JSON:
        {{
            "decision": "approve|defer|escalate",
            "action": "renew_certificate",
            "confidence": 0-1,
            "reason": "explanation"
        }}
        
        If expiring in < 7 days → approve renewal
        If < 3 days → escalate
        Otherwise defer
        """
        
        try:
            # Try Groq first (higher quota, faster)
            if groq_client:
                logger.info("🚀 Using Groq AI for SSL analysis")
                response_text = call_groq_llm(prompt)
                data = extract_json_from_response(response_text)
            else:
                # Fallback to Gemini
                logger.info("🔄 Using Gemini for SSL analysis")
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
                data = extract_json_from_response(response.text)
            
            return AgentDecision(
                agent_name=self.name,
                decision=data.get("decision", "defer"),
                action=ActionType.RENEW_CERTIFICATE,
                confidence=data.get("confidence", 0),
                context={"certificate": cert, "analysis": data}
            )
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            return None
    
    async def _execute_decision(self, decision: AgentDecision):
        """Execute autonomous action"""
        logger.info(f"🤖 {self.name} → {decision.decision.upper()} ({decision.confidence:.0%})")
        
        if decision.decision == "approve":
            # Renew certificate
            result = await self._autonomous_renew(decision.context["certificate"])
            decision.executed = True
            decision.result = result
            logger.info(f"✅ Certificate renewed: {decision.context['certificate']['domain']}")
        
        elif decision.decision == "escalate":
            # Create Jira + notify team
            await self._create_jira_and_notify(decision)
    
    async def _autonomous_renew(self, cert: Dict) -> Dict:
        """Autonomous certificate renewal (stub)"""
        logger.info(f"🔄 Renewing certificate for {cert['domain']}...")
        # Placeholder: Would call Venefi/Let's Encrypt APIs
        return {"success": True, "domain": cert["domain"], "renewed_at": datetime.now().isoformat()}
    
    async def _create_jira_and_notify(self, decision: AgentDecision):
        """Create Jira ticket and notify (stub)"""
        logger.info(f"🎫 Creating Jira ticket for {decision.context['certificate']['domain']}...")


class VulnerabilityRemediationAgent:
    """Agent: Autonomous Vulnerability Patching"""
    
    def __init__(self, client: genai.Client, model: str = "models/gemini-2.5-flash"):
        self.client = client
        self.model = model
        self.name = "Vulnerability Remediation Agent"
        self.last_run = None
    
    async def monitor(self):
        """Continuously scan for vulnerabilities and remediate"""
        while True:
            try:
                vulnerabilities = await self._fetch_vulnerabilities()
                
                for vuln in vulnerabilities:
                    decision = await self._assess_vulnerability(vuln)
                    
                    if decision and decision.confidence > 0.8:  # High confidence needed
                        await self._execute_remediation(decision)
                        
                self.last_run = datetime.now()
            except Exception as e:
                logger.error(f"❌ {self.name} error: {str(e)}")
            
            # Run every 6 hours
            await asyncio.sleep(21600)
    
    async def _fetch_vulnerabilities(self) -> List[Dict]:
        """Fetch from Tableau, security scanners, NVD"""
        # Placeholder
        return [
            {"cve": "CVE-2024-1234", "severity": "high", "affected_systems": ["web-01"]},
            {"cve": "CVE-2024-5678", "severity": "critical", "affected_systems": ["db-01", "db-02"]},
        ]
    
    async def _assess_vulnerability(self, vuln: Dict) -> Optional[AgentDecision]:
        """LLM-powered vulnerability assessment (Groq with Gemini fallback)"""
        prompt = f"""
        Assess this vulnerability for autonomous remediation:
        CVE: {vuln['cve']}
        Severity: {vuln['severity']}
        Affected Systems: {', '.join(vuln['affected_systems'])}
        
        Return JSON:
        {{
            "decision": "approve|defer|escalate",
            "action": "patch_vulnerability",
            "remediation_steps": ["step1", "step2", ...],
            "confidence": 0-1,
            "risk": "patch_risk_assessment"
        }}
        
        Approve if patch is stable & low-risk
        Defer if requires testing
        Escalate if critical + complex
        """
        
        try:
            # Try Groq first (higher quota)
            if groq_client:
                logger.info("🚀 Using Groq AI for vulnerability analysis")
                response_text = call_groq_llm(prompt)
                data = extract_json_from_response(response_text)
            else:
                # Fallback to Gemini
                logger.info("🔄 Using Gemini for vulnerability analysis")
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
                data = extract_json_from_response(response.text)
            
            return AgentDecision(
                agent_name=self.name,
                decision=data.get("decision", "defer"),
                action=ActionType.PATCH_VULNERABILITY,
                confidence=data.get("confidence", 0),
                context={"vulnerability": vuln, "analysis": data}
            )
        except Exception as e:
            logger.error(f"Assessment error: {str(e)}")
            return None
    
    async def _execute_remediation(self, decision: AgentDecision):
        """Execute vulnerability patch autonomously"""
        logger.info(f"🤖 {self.name} → {decision.decision.upper()} ({decision.confidence:.0%})")
        logger.info(f"📋 Steps: {decision.context['analysis'].get('remediation_steps', [])}")
        
        if decision.decision == "approve":
            # Execute patch steps
            result = await self._apply_patches(decision.context["vulnerability"])
            decision.executed = True
            decision.result = result
            logger.info(f"✅ Vulnerability patched: {decision.context['vulnerability']['cve']}")
    
    async def _apply_patches(self, vuln: Dict) -> Dict:
        """Apply vulnerability patches (stub)"""
        logger.info(f"🔧 Applying patches for {vuln['cve']}...")
        # Placeholder: Would execute patch automation
        return {"success": True, "cve": vuln["cve"], "patched_at": datetime.now().isoformat()}


class HealthCheckAgent:
    """Agent: Autonomous System Health Monitoring"""
    
    def __init__(self, client: genai.Client, model: str = "models/gemini-2.5-flash"):
        self.client = client
        self.model = model
        self.name = "Health Check Agent"
        self.last_run = None
        self.health_history = {}
        # Docker container mapping (AppName -> container_name)
        self.docker_containers = {
            "AuthService": "auth-service",
            "PaymentAPI": "payment-api",
            "UserService": "user-service",
            "OrderService": "order-service",
            "InventoryAPI": "inventory-api",
            "FlakyService": "flaky-service"
        }
        # Docker container mapping (AppName -> container_name)
        self.docker_containers = {
            "AuthService": "auth-service",
            "PaymentAPI": "payment-api",
            "UserService": "user-service",
            "OrderService": "order-service",
            "InventoryAPI": "inventory-api",
            "FlakyService": "flaky-service"
        }
    
    async def monitor(self):
        """Continuously monitor system health"""
        while True:
            try:
                metrics = await self._collect_metrics()
                decision = await self._analyze_health(metrics)
                
                if decision and decision.decision != "healthy":
                    await self._execute_remediation(decision)
                    
                self.last_run = datetime.now()
            except Exception as e:
                logger.error(f"❌ {self.name} error: {str(e)}")
            
            # Run every 2 hours (reduced to save API quota)
            await asyncio.sleep(7200)
    
    async def _collect_metrics(self) -> Dict:
        """Collect metrics by checking URLs from apps.csv"""
        apps_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "apps.csv")
        
        down_apps = []
        total_apps = 0
        
        try:
            with open(apps_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    app_name = row.get('AppName', '').strip()
                    url = row.get('URL', '').strip()
                    
                    if not app_name or not url:
                        continue
                    
                    total_apps += 1
                    
                    # Check URL health
                    try:
                        response = requests.get(url, timeout=5)
                        if response.status_code >= 400:
                            down_apps.append({"app": app_name, "url": url, "status": response.status_code})
                            logger.warning(f"⚠️ {app_name} is DOWN (HTTP {response.status_code})")
                    except Exception as e:
                        down_apps.append({"app": app_name, "url": url, "error": str(e)})
                        logger.warning(f"⚠️ {app_name} is UNREACHABLE: {str(e)}")
        
        except Exception as e:
            logger.error(f"Failed to read apps.csv: {str(e)}")
        
        return {
            "total_apps": total_apps,
            "down_apps": down_apps,
            "down_count": len(down_apps),
            "health_percentage": ((total_apps - len(down_apps)) / total_apps * 100) if total_apps > 0 else 100
        }
    
    async def _analyze_health(self, metrics: Dict) -> Optional[AgentDecision]:
        """Analyzes health and decides if remediation needed (skips LLM to save quota)"""
        if metrics.get("down_count", 0) == 0:
            return None  # All services healthy
        
        # Skip LLM analysis - if services are down, just restart them
        # This saves API quota (free tier = 20 calls/day)
        down_apps = metrics.get('down_apps', [])
        apps_to_restart = [app['app'] for app in down_apps]
        
        logger.info(f"⚠️ Detected {len(apps_to_restart)} down services: {apps_to_restart}")
        
        # Create decision without LLM analysis
        data = {
            "status": "critical" if len(apps_to_restart) > 2 else "degraded",
            "action": "restart_docker",
            "confidence": 1.0,  # High confidence for simple down detection
            "apps_to_restart": apps_to_restart,
            "recommendation": f"Restart {len(apps_to_restart)} down services"
        }
        
        # Optional: Use LLM only for complex scenarios (uncomment if you have paid API)
        # prompt = f"""
        # Analyze application health status:
        # {json.dumps(metrics, indent=2)}
        # 
        # There are {metrics['down_count']} services DOWN out of {metrics['total_apps']} total.
        # Down services: {[app['app'] for app in metrics.get('down_apps', [])]}
        # 
        # Return JSON:
        # {{
        #     "status": "healthy|degraded|critical",
        #     "action": "restart_service|restart_docker|none",
        #     "confidence": 0-1,
        #     "apps_to_restart": ["list of app names to restart"],
        #     "recommendation": "what_to_do"
        # }}
        # """
        
        # LLM call skipped to save API quota - using simple rule-based decision
        # try:
        #     response = self.client.models.generate_content(
        #         model=self.model,
        #         contents=prompt
        #     )
        #     
        #     data = extract_json_from_response(response.text)
        #     
        #     if data.get("status") == "healthy":
        #         return None
        
        return AgentDecision(
                agent_name=self.name,
                decision="approve",  # Always approve restart for down services
                action=ActionType.RESTART_SERVICE,
                confidence=data.get("confidence", 1.0),
                context={
                    "metrics": metrics,
                    "analysis": data,
                    "down_apps": metrics.get("down_apps", []),
                    "apps_to_restart": data.get("apps_to_restart", [])
                }
            )
    
    async def _execute_remediation(self, decision: AgentDecision):
        """Execute health remediation autonomously"""
        logger.info(f"🤖 {self.name} → {decision.decision.upper()}")
        logger.info(f"📋 Action: {decision.action.value}")
        
        if decision.decision == "approve":
            await self._apply_remediation(decision.context["analysis"])
            decision.executed = True
    
    async def _apply_remediation(self, analysis: Dict):
        """Apply health remediation - restart Docker containers for down services"""
        action = analysis.get("action", "none")
        logger.info(f"⚙️ Applying remediation: {action}...")
        
        if "restart" in action:
            apps_to_restart = analysis.get("apps_to_restart", [])
            
            for app_name in apps_to_restart:
                container_name = self.docker_containers.get(app_name)
                
                if container_name:
                    logger.info(f"♻️ Restarting Docker container: {container_name} (for {app_name})")
                    restart_success = await self._restart_docker_container(container_name)
                    
                    if restart_success:
                        logger.info(f"✅ Successfully restarted {container_name}")
                        # Wait a bit for service to start
                        await asyncio.sleep(5)
                        # Re-check health
                        await self._verify_service_health(app_name)
                    else:
                        logger.error(f"❌ Failed to restart {container_name}")
                else:
                    logger.warning(f"⚠️ No Docker mapping for {app_name} - manual intervention required")
    
    async def _restart_docker_container(self, container_name: str) -> bool:
        """Restart a Docker container"""
        try:
            # Stop container
            logger.info(f"🛑 Stopping container: {container_name}")
            subprocess.run(["docker", "stop", container_name], capture_output=True, timeout=30)
            
            # Start container
            logger.info(f"▶️ Starting container: {container_name}")
            result = subprocess.run(["docker", "start", container_name], capture_output=True, timeout=30, text=True)
            
            if result.returncode == 0:
                return True
            else:
                logger.error(f"Docker start failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout restarting container: {container_name}")
            return False
        except FileNotFoundError:
            logger.error("Docker command not found - is Docker installed?")
            return False
        except Exception as e:
            logger.error(f"Error restarting container: {str(e)}")
            return False
    
    async def _verify_service_health(self, app_name: str):
        """Verify service is healthy after restart"""
        apps_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "apps.csv")
        
        try:
            with open(apps_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('AppName', '').strip() == app_name:
                        url = row.get('URL', '').strip()
                        try:
                            response = requests.get(url, timeout=5)
                            if response.status_code < 400:
                                logger.info(f"✅ {app_name} is now HEALTHY (HTTP {response.status_code})")
                            else:
                                logger.warning(f"⚠️ {app_name} still unhealthy (HTTP {response.status_code})")
                        except Exception as e:
                            logger.warning(f"⚠️ {app_name} health check failed: {str(e)}")
                        break
        except Exception as e:
            logger.error(f"Failed to verify health: {str(e)}")


class ProblemDetectionAgent:
    """Agent: Autonomous Problem Detection & Jira Creation"""
    
    def __init__(self, client: genai.Client, model: str = "models/gemini-2.5-flash"):
        self.client = client
        self.model = model
        self.name = "Problem Detection Agent"
        self.last_run = None
    
    async def monitor(self):
        """Continuously detect problems"""
        while True:
            try:
                problems = await self._detect_problems()
                
                for problem in problems:
                    # Check if already solved by other agents
                    if not await self._is_solved_by_agents(problem):
                        await self._create_jira_ticket(problem)
                        
                self.last_run = datetime.now()
            except Exception as e:
                logger.error(f"❌ {self.name} error: {str(e)}")
            
            # Run every 15 minutes
            await asyncio.sleep(900)
    
    async def _detect_problems(self) -> List[Dict]:
        """Detect problems from logs, metrics, alerts"""
        # Placeholder
        return []
    
    async def _is_solved_by_agents(self, problem: Dict) -> bool:
        """Check if another agent already fixed this"""
        # Would check execution results
        return False
    
    async def _create_jira_ticket(self, problem: Dict):
        """Auto-create Jira ticket"""
        logger.info(f"🎟️ Auto-creating Jira ticket for: {problem.get('title')}")
        # Would call Jira API


# ============== Autonomous Agent Orchestrator ==============

class AutonomousAgentService:
    """Main service orchestrating all autonomous agents"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=self.api_key)
        
        # Initialize agents
        self.agents = {
            "ssl": SSLCertificateAgent(self.client),
            "vulnerability": VulnerabilityRemediationAgent(self.client),
            "health": HealthCheckAgent(self.client),
            "problems": ProblemDetectionAgent(self.client),
        }
        
        self.running = False
        self.agent_threads = {}
        self.decisions_log = []
        
        logger.info("✅ Autonomous Agent Service initialized")
    
    def start(self):
        """Start all agents in background (only if AUTO_RUN_AGENTS=true)"""
        if self.running:
            logger.warning("Service already running")
            return
        
        # Check if auto-run is enabled
        auto_run = os.getenv("AUTO_RUN_AGENTS", "false").lower() == "true"
        
        if not auto_run:
            logger.info("⏸️  AUTO_RUN_AGENTS=false - Agents are in MANUAL mode (won't consume API quota)")
            logger.info("💡 Agents will only run when triggered via API endpoints")
            logger.info("💡 To enable automatic monitoring, set AUTO_RUN_AGENTS=true in .env")
            self.running = False  # Keep agents stopped
            return
        
        self.running = True
        logger.info("🚀 Starting Autonomous Agent Service (AUTO_RUN_AGENTS=true)...")
        
        # Start each agent in separate thread with its own event loop
        for agent_name, agent in self.agents.items():
            thread = threading.Thread(
                target=self._run_agent_monitor,
                args=(agent,),
                daemon=True,
                name=f"agent-{agent_name}"
            )
            thread.start()
            self.agent_threads[agent_name] = thread
            logger.info(f"✅ {agent.name} started")
    
    def _run_agent_monitor(self, agent):
        """Run agent monitor in its own event loop (for threading)"""
        try:
            asyncio.run(agent.monitor())
        except Exception as e:
            logger.error(f"❌ Agent {agent.name} failed: {str(e)}")
    
    def stop(self):
        """Stop all agents"""
        self.running = False
        logger.info("🛑 Stopping Autonomous Agent Service...")
    
    def get_status(self) -> Dict:
        """Get service status"""
        return {
            "running": self.running,
            "agents": {
                name: {
                    "name": agent.name,
                    "last_run": agent.last_run.isoformat() if agent.last_run else None,
                    "active": self.agent_threads.get(name, {}).is_alive() if name in self.agent_threads else False
                }
                for name, agent in self.agents.items()
            },
            "total_decisions": len(self.decisions_log),
            "executed_actions": sum(1 for d in self.decisions_log if d.executed)
        }
    
    def get_decisions(self, limit: int = 50) -> List[Dict]:
        """Get recent autonomous decisions"""
        return [
            {
                "agent": d.agent_name,
                "decision": d.decision,
                "action": d.action.value,
                "confidence": d.confidence,
                "timestamp": d.timestamp.isoformat(),
                "executed": d.executed,
                "result": d.result
            }
            for d in self.decisions_log[-limit:]
        ]


# Global service instance
autonomous_service: Optional[AutonomousAgentService] = None

def initialize_service(api_key: Optional[str] = None):
    """Initialize global service"""
    global autonomous_service
    autonomous_service = AutonomousAgentService(api_key)

def get_service() -> AutonomousAgentService:
    """Get service instance"""
    global autonomous_service
    if not autonomous_service:
        autonomous_service = AutonomousAgentService()
    return autonomous_service
