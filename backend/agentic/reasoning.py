# backend/agentic/reasoning.py
"""
REASONING ENGINE: LLM-powered autonomous decision-making
Uses Gemini to analyze incidents and recommend remediation actions
"""

import os
import json
import logging
from typing import Dict, Any, List
from google import genai

from .core import Incident, ReasoningDecision, Memory


logger = logging.getLogger(__name__)


class LLMReasoner:
    """Gemini-powered reasoning engine"""

    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY not set")
        self.client = genai.Client(api_key=api_key)

    def reason_about_incident(
        self, incident: Incident, memory: Memory
    ) -> ReasoningDecision:
        """
        Full LLM reasoning about incident:
        1. Analyze incident signals
        2. Consider similar past incidents
        3. Review effective remediation patterns
        4. Recommend best actions
        5. Assess risk level and approval need
        """

        # Get context from memory
        similar_incidents = memory.get_similar_incidents(incident.app_name, days=30)
        pattern_rec = memory.get_pattern_recommendations(
            incident.description.split()[0]  # First word as root cause hint
        )

        # Build LLM prompt
        prompt = self._build_reasoning_prompt(incident, similar_incidents, pattern_rec)

        try:
            # Call Gemini with strict JSON output
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )

            # Parse response
            response_text = response.text.strip()
            reasoning_json = self._extract_json(response_text)

            if not reasoning_json:
                logger.warning(f"Could not parse reasoning output, using fallback")
                return self._fallback_reasoning(incident)

            # Construct decision
            decision = ReasoningDecision(
                incident_id=incident.id,
                reasoning=reasoning_json.get("reasoning", ""),
                recommended_actions=reasoning_json.get("recommended_actions", []),
                confidence=reasoning_json.get("confidence", 0.7),
                risk_level=reasoning_json.get("risk_level", "medium"),
                requires_approval=reasoning_json.get("requires_approval", False),
                escalation_needed=reasoning_json.get("escalation_needed", False),
            )

            logger.info(
                f"[REASONING] {incident.id}: Actions={decision.recommended_actions}, "
                f"Risk={decision.risk_level}, Confidence={decision.confidence:.1%}"
            )
            return decision

        except Exception as e:
            logger.error(f"Reasoning error: {e}")
            return self._fallback_reasoning(incident)

    def _build_reasoning_prompt(
        self,
        incident: Incident,
        similar_incidents: List[Dict],
        pattern_rec: Dict,
    ) -> str:
        """Build LLM prompt for incident reasoning"""
        return f"""
You are an expert SRE assistant analyzing production incidents.

INCIDENT DETAILS:
- ID: {incident.id}
- App: {incident.app_name}
- Severity: {incident.severity.value}
- Description: {incident.description}
- Detected at: {incident.timestamp}

SIGNALS DETECTED:
{json.dumps([s.to_dict() for s in incident.signals], indent=2)}

SIMILAR RECENT INCIDENTS:
{json.dumps(similar_incidents[:3], indent=2)}

EFFECTIVE REMEDIATION PATTERNS:
{json.dumps(pattern_rec, indent=2)}

CONTEXT:
{json.dumps(incident.context, indent=2)}

TASK:
Analyze this incident and provide:
1. Root cause hypothesis (1 sentence)
2. Recommended remediation actions (list of action names: restart_service, scale_up, drain_connections, etc.)
3. Risk level assessment (low, medium, high)
4. Whether approval is required (boolean)
5. Whether escalation is needed (boolean)
6. Confidence in your recommendation (0.0-1.0)

You MUST return ONLY valid JSON (no markdown, no code fences) with this exact structure:
{{
  "root_cause": "...",
  "reasoning": "Step-by-step reasoning...",
  "recommended_actions": ["action1", "action2"],
  "risk_level": "low|medium|high",
  "requires_approval": false,
  "escalation_needed": false,
  "confidence": 0.85
}}

Focus on:
- Safe remediation (prefer restart over scale-down)
- Learning from patterns (prioritize actions that worked before)
- Risk mitigation (high severity requires approval)
- Quick resolution (prioritize fast-acting vs time-consuming)
"""

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from response"""
        try:
            # Try direct parse
            return json.loads(text)
        except:
            pass

        # Try to find JSON block
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass

        return None

    def _fallback_reasoning(self, incident: Incident) -> ReasoningDecision:
        """Fallback rule-based reasoning if LLM fails"""
        actions = []
        requires_approval = False
        escalate = False

        if incident.severity.value == "CRITICAL":
            actions = ["restart_service", "notify_oncall"]
            requires_approval = True
            escalate = True
        elif incident.severity.value == "HIGH":
            actions = ["check_logs", "restart_service"]
            requires_approval = True
        else:
            actions = ["check_logs", "monitor"]

        return ReasoningDecision(
            incident_id=incident.id,
            reasoning="Fallback rule-based reasoning (LLM unavailable)",
            recommended_actions=actions,
            confidence=0.6,
            risk_level="medium" if incident.severity.value == "HIGH" else "low",
            requires_approval=requires_approval,
            escalation_needed=escalate,
        )


class ContextualAnalyzer:
    """Provides incident context enrichment"""

    def __init__(self, memory: Memory):
        self.memory = memory

    def get_incident_context(self, app_name: str) -> Dict[str, Any]:
        """Gather full context about app and past incidents"""
        similar = self.memory.get_similar_incidents(app_name, days=30)
        patterns = {}

        for inc in similar:
            root_cause = inc.get("root_cause_confirmed")
            if root_cause:
                if root_cause not in patterns:
                    patterns[root_cause] = {"count": 0, "avg_mttr": 0}
                patterns[root_cause]["count"] += 1

        return {
            "app_name": app_name,
            "recent_incidents": len(similar),
            "common_root_causes": list(patterns.keys()),
            "patterns": patterns,
            "last_incident": similar[0] if similar else None,
        }
