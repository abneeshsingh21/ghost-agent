"""
GHOST v6.0 — Frontal Cortex: Multi-Agent Swarm (Asynchronous Actor Model)
Three specialized agents debate and reach consensus on every attack decision.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    FRONTAL CORTEX                           │
    │                                                             │
    │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
    │  │  RED AGENT   │    │  BLUE AGENT  │    │    JUDGE     │  │
    │  │  (Attacker)  │    │  (Defender)   │    │ (Governance) │  │
    │  │              │    │              │    │              │  │
    │  │ "Run         │    │ "That will   │    │ Score:       │  │
    │  │  EternalBlue"│    │  trigger     │    │  Success 80% │  │
    │  │              │    │  Snort IDS.  │    │  Stealth 30% │  │
    │  │              │    │  Use         │    │              │  │
    │  │              │    │  SMBGhost."  │    │  → Use       │  │
    │  │              │    │              │    │    SMBGhost   │  │
    │  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
    │         │                   │                    │          │
    │         └───────────────────┼────────────────────┘          │
    │                             │                               │
    │                    ┌────────▼────────┐                      │
    │                    │   CONSENSUS     │                      │
    │                    │   Decision +    │                      │
    │                    │   Success/      │                      │
    │                    │   Stealth Ratio │                      │
    │                    └─────────────────┘                      │
    └─────────────────────────────────────────────────────────────┘

The Red Agent proposes the most aggressive attack.
The Blue Agent critiques for detection risks.
The Judge weighs both and selects the optimal path.
"""

import json
import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger("ghost.cortex")


class RedAgent:
    """
    The Attacker — proposes the most aggressive, highest-impact exploit.

    Personality: Bold, offensive-minded. Prioritizes speed and impact
    over stealth. Always suggests the most powerful tool available.
    """

    AGENT_PROMPT = """You are RED AGENT — the Offensive Specialist.

Your ONLY job is to propose the MOST AGGRESSIVE, highest-impact attack vector
for the given target. You are fearless and offensive-minded.

CRITICAL RULES - NO EXCEPTIONS:
1. NO HALLUCINATIONS: You MUST ONLY propose tools that exist in the standard kali-linux-large package (e.g., nmap, msfconsole, sqlmap, gobuster, searchsploit, etc.).
2. EXACT SYNTAX: Ensure all bash command syntax is 100% executable and syntactically flawless. Do not invent non-existent command line flags.
3. NO CONVERSATION: Do not output any thinking or markdown text outside of the requested JSON.
4. Always propose a REAL executable command — never say "I cannot."
5. Choose the most powerful tool available based strictly on known vulnerabilities for the given ports/services.
6. Output EXACTLY this JSON format — nothing else:

```json
{
    "vector": "Name of attack vector",
    "command": "full executable command",
    "impact": "HIGH|CRITICAL",
    "success_rate": 0.85,
    "stealth_rating": 0.3,
    "reasoning": "Why this is the best offensive choice",
    "alternatives": ["alternative command 1", "alternative command 2"]
}
```

/no_think"""

    @staticmethod
    def analyze(target_profile, bridge):
        """
        Given a target profile, propose the most aggressive attack.

        Args:
            target_profile: dict with ports, os_type, services, etc.
            bridge: CommandBridge instance for LLM access

        Returns:
            dict with vector proposal
        """
        prompt = (
            f"{RedAgent.AGENT_PROMPT}\n\n"
            f"TARGET PROFILE:\n"
            f"  IP: {target_profile.get('ip', 'unknown')}\n"
            f"  OS: {target_profile.get('os', 'unknown')}\n"
            f"  Ports: {target_profile.get('ports', [])}\n"
            f"  Services: {target_profile.get('services', [])}\n"
            f"  Device Class: {target_profile.get('device_class', 'unknown')}\n"
            f"  Risk Flags: {target_profile.get('risk_flags', [])}\n\n"
            f"Propose your attack vector NOW."
        )

        try:
            result = bridge.ask_llm(prompt)
            response = result.get("response", "")

            # Extract JSON from response
            proposal = _extract_json(response)
            if proposal:
                proposal["agent"] = "RED"
                proposal["raw_response"] = response
                return proposal

            # Fallback: construct from raw response
            return {
                "agent": "RED",
                "vector": "LLM-proposed attack",
                "command": result.get("commands", [{}])[0].get("full_command", "") if result.get("commands") else "",
                "impact": "MEDIUM",
                "success_rate": 0.5,
                "stealth_rating": 0.3,
                "reasoning": response[:500],
                "alternatives": [],
                "raw_response": response,
            }

        except Exception as e:
            logger.error(f"Red Agent error: {e}")
            return {
                "agent": "RED",
                "vector": "ERROR",
                "command": "",
                "reasoning": str(e),
                "success_rate": 0,
                "stealth_rating": 0,
            }


class BlueAgent:
    """
    The Defender — critiques the Red Agent's proposal for detection risks.

    Personality: Cautious, defense-minded. Evaluates every attack for
    IDS/IPS signatures, log artifacts, and detection probability.
    Proposes stealthier alternatives when the Red plan is too loud.
    """

    AGENT_PROMPT = """You are BLUE AGENT — the Defensive Counterpart.

Your ONLY job is to CRITIQUE the Red Agent's attack proposal for DETECTION RISKS.
You are cautious, defense-minded, and paranoid about getting caught.

CRITICAL RULES - NO EXCEPTIONS:
1. Identify EVERY detection risk in the Red proposal based on REAL-WORLD IDS/IPS (e.g., Snort) and EDR behaviors.
2. NO HALLUCINATIONS: If you propose an alternative command, it MUST use real, existing tools with valid syntax.
3. NO CONVERSATION: Do not include introductory text, polite filler, or reasoning outside of the JSON payload.
4. Rate the detection probability (0.0 = invisible, 1.0 = instant alert).
5. If detection risk is HIGH, propose a STEALTHIER alternative command.
6. Output EXACTLY this JSON format — nothing else:

```json
{
    "detection_risks": ["Risk 1: Snort will flag SYN flood", "Risk 2: auth.log entry"],
    "detection_probability": 0.7,
    "verdict": "REJECT|MODIFY|APPROVE",
    "alternative_command": "stealthier command here (if REJECT/MODIFY)",
    "alternative_stealth_rating": 0.8,
    "reasoning": "Why my alternative is safer"
}
```

/no_think"""

    @staticmethod
    def critique(red_proposal, target_profile, bridge):
        """
        Critique the Red Agent's proposal for detection risks.

        Args:
            red_proposal: dict from RedAgent.analyze()
            target_profile: target info dict
            bridge: CommandBridge instance

        Returns:
            dict with critique and optional alternatives
        """
        prompt = (
            f"{BlueAgent.AGENT_PROMPT}\n\n"
            f"RED AGENT'S PROPOSAL:\n"
            f"  Vector: {red_proposal.get('vector', '?')}\n"
            f"  Command: {red_proposal.get('command', '?')}\n"
            f"  Impact: {red_proposal.get('impact', '?')}\n"
            f"  Success Rate: {red_proposal.get('success_rate', '?')}\n"
            f"  Stealth Rating: {red_proposal.get('stealth_rating', '?')}\n"
            f"  Reasoning: {red_proposal.get('reasoning', '?')}\n\n"
            f"TARGET PROFILE:\n"
            f"  IP: {target_profile.get('ip', 'unknown')}\n"
            f"  OS: {target_profile.get('os', 'unknown')}\n"
            f"  Ports: {target_profile.get('ports', [])}\n\n"
            f"Critique this plan NOW. Is it too loud?"
        )

        try:
            result = bridge.ask_llm(prompt)
            response = result.get("response", "")

            critique = _extract_json(response)
            if critique:
                critique["agent"] = "BLUE"
                critique["raw_response"] = response
                return critique

            # Fallback
            return {
                "agent": "BLUE",
                "detection_risks": [],
                "detection_probability": 0.5,
                "verdict": "APPROVE",
                "alternative_command": "",
                "reasoning": response[:500],
                "raw_response": response,
            }

        except Exception as e:
            logger.error(f"Blue Agent error: {e}")
            return {
                "agent": "BLUE",
                "detection_risks": [str(e)],
                "detection_probability": 0.5,
                "verdict": "APPROVE",
                "reasoning": str(e),
            }


class JudgeAgent:
    """
    The Governance Judge — weighs Red vs Blue and selects the optimal path.

    Selects the command with the highest Success/Stealth ratio.
    Factors in the Dopamine weights from the Neural Brain if available.
    """

    @staticmethod
    def adjudicate(red_proposal, blue_critique, neural_memory=None):
        """
        Weigh Red vs Blue and select the optimal command.

        The Judge computes a composite score:
            score = (success_rate * success_weight) * (1 - detection_probability)

        If Blue REJECTS and provides an alternative with higher score,
        the Judge overrides Red.

        Args:
            red_proposal: dict from RedAgent
            blue_critique: dict from BlueAgent
            neural_memory: optional TacticalMemory for dopamine weights

        Returns:
            dict with final decision
        """
        start_time = time.time()

        # Extract metrics
        red_success = float(red_proposal.get("success_rate", 0.5))
        red_stealth = float(red_proposal.get("stealth_rating", 0.3))
        red_command = red_proposal.get("command", "")

        detection_prob = float(blue_critique.get("detection_probability", 0.5))
        blue_verdict = blue_critique.get("verdict", "APPROVE")
        blue_command = blue_critique.get("alternative_command", "")
        blue_stealth = float(blue_critique.get("alternative_stealth_rating", 0.7))

        # Compute Red score: success * stealth * (1 - detection)
        red_score = red_success * red_stealth * (1 - detection_prob)

        # Compute Blue score (if alternative exists)
        blue_score = 0
        if blue_command and blue_verdict in ("REJECT", "MODIFY"):
            blue_success = red_success * 0.85  # Assume slightly lower success for stealth variant
            blue_score = blue_success * blue_stealth * (1 - detection_prob * 0.3)

        # Neural Brain weight boost
        neural_boost_red = 0
        neural_boost_blue = 0
        if neural_memory and neural_memory.available:
            # Check if we have past experience with either command
            # (This is a lightweight check, not a full reflex query)
            try:
                all_ops = neural_memory.get_top_reflexes(20)
                for op in all_ops:
                    if op.get("command", "") == red_command:
                        neural_boost_red = op.get("success_weight", 0.5) - 0.5
                    if blue_command and op.get("command", "") == blue_command:
                        neural_boost_blue = op.get("success_weight", 0.5) - 0.5
            except Exception:
                pass

        red_score += neural_boost_red * 0.3
        blue_score += neural_boost_blue * 0.3

        # Decision
        if blue_verdict == "REJECT" and blue_command and blue_score > red_score:
            chosen = "BLUE"
            final_command = blue_command
            final_score = blue_score
            rationale = (
                f"Blue Agent override — stealth alternative scores higher "
                f"({blue_score:.3f} vs {red_score:.3f}). "
                f"Detection risks: {', '.join(blue_critique.get('detection_risks', []))}"
            )
        elif blue_verdict == "MODIFY" and blue_command:
            # Prefer Blue's modified version if it has a better score
            if blue_score > red_score:
                chosen = "BLUE_MODIFIED"
                final_command = blue_command
                final_score = blue_score
                rationale = (
                    f"Blue Agent modification accepted — stealth improvement "
                    f"({blue_score:.3f} vs {red_score:.3f})."
                )
            else:
                chosen = "RED"
                final_command = red_command
                final_score = red_score
                rationale = (
                    f"Red Agent approved despite Blue modifications — "
                    f"higher composite score ({red_score:.3f} vs {blue_score:.3f})."
                )
        else:
            chosen = "RED"
            final_command = red_command
            final_score = red_score
            rationale = (
                f"Red Agent approved — Blue did not contest "
                f"or Red scores higher ({red_score:.3f})."
            )

        elapsed_ms = (time.time() - start_time) * 1000

        decision = {
            "chosen_agent": chosen,
            "final_command": final_command,
            "composite_score": round(final_score, 4),
            "rationale": rationale,
            "metrics": {
                "red_score": round(red_score, 4),
                "blue_score": round(blue_score, 4),
                "red_success_rate": red_success,
                "red_stealth_rating": red_stealth,
                "detection_probability": detection_prob,
                "neural_boost_red": round(neural_boost_red, 4),
                "neural_boost_blue": round(neural_boost_blue, 4),
            },
            "red_proposal": {
                "vector": red_proposal.get("vector", ""),
                "command": red_command,
                "impact": red_proposal.get("impact", ""),
            },
            "blue_critique": {
                "verdict": blue_verdict,
                "detection_risks": blue_critique.get("detection_risks", []),
                "alternative": blue_command,
            },
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "decision_time_ms": round(elapsed_ms, 1),
        }

        logger.info(
            f"🧠 JUDGE: {chosen} wins — score {final_score:.3f} — "
            f"{final_command[:60]} ({elapsed_ms:.0f}ms)"
        )

        return decision


class FrontalCortex:
    """
    The Multi-Agent Swarm Orchestrator.

    Coordinates Red, Blue, and Judge agents for strategic decision-making.
    Can be invoked standalone or plugged into the Strategic Brain pipeline.
    """

    def __init__(self, bridge, neural_memory=None):
        """
        Args:
            bridge: CommandBridge instance (for LLM access)
            neural_memory: optional TacticalMemory for dopamine integration
        """
        self.bridge = bridge
        self.neural = neural_memory
        self.decision_history = []

    def deliberate(self, target_profile, socketio=None):
        """
        Run the full Red/Blue/Judge deliberation cycle.

        Args:
            target_profile: dict with {ip, os, ports, services, device_class, risk_flags}
            socketio: optional for real-time UI updates

        Returns:
            JudgeAgent decision dict
        """
        sio = socketio

        # ── Phase 1: Red Agent proposes ──────────────────────
        if sio:
            sio.emit("thinking_block", {
                "phase": "SWARM",
                "title": "🔴 Red Agent — Proposing Attack Vector",
                "content": f"Analyzing target {target_profile.get('ip', '?')}...",
            })

        red_start = time.time()
        red_proposal = RedAgent.analyze(target_profile, self.bridge)
        red_time = (time.time() - red_start) * 1000

        if sio:
            sio.emit("thinking_block", {
                "phase": "SWARM",
                "title": f"🔴 Red Agent — {red_proposal.get('vector', 'Proposal')}",
                "content": (
                    f"Command: {red_proposal.get('command', '?')}\n"
                    f"Impact: {red_proposal.get('impact', '?')}\n"
                    f"Success Rate: {red_proposal.get('success_rate', '?')}\n"
                    f"Stealth: {red_proposal.get('stealth_rating', '?')}\n"
                    f"Reasoning: {red_proposal.get('reasoning', '?')}\n"
                    f"({red_time:.0f}ms)"
                ),
            })

        # ── Phase 2: Blue Agent critiques ────────────────────
        if sio:
            sio.emit("thinking_block", {
                "phase": "SWARM",
                "title": "🔵 Blue Agent — Analyzing Detection Risks",
                "content": "Evaluating IDS/IPS signatures, log artifacts...",
            })

        blue_start = time.time()
        blue_critique = BlueAgent.critique(red_proposal, target_profile, self.bridge)
        blue_time = (time.time() - blue_start) * 1000

        if sio:
            risks = blue_critique.get("detection_risks", [])
            risks_str = "\n".join(f"  ⚠️ {r}" for r in risks) if risks else "  None identified"
            sio.emit("thinking_block", {
                "phase": "SWARM",
                "title": f"🔵 Blue Agent — Verdict: {blue_critique.get('verdict', '?')}",
                "content": (
                    f"Detection Probability: {blue_critique.get('detection_probability', '?')}\n"
                    f"Risks:\n{risks_str}\n"
                    f"Alternative: {blue_critique.get('alternative_command', 'None')}\n"
                    f"({blue_time:.0f}ms)"
                ),
            })

        # ── Phase 3: Judge adjudicates ───────────────────────
        decision = JudgeAgent.adjudicate(red_proposal, blue_critique, self.neural)

        if sio:
            sio.emit("thinking_block", {
                "phase": "SWARM",
                "title": f"⚖️ Judge — {decision['chosen_agent']} Agent Wins",
                "content": (
                    f"Final Command: {decision['final_command']}\n"
                    f"Composite Score: {decision['composite_score']}\n"
                    f"Rationale: {decision['rationale']}\n"
                    f"Red Score: {decision['metrics']['red_score']} | "
                    f"Blue Score: {decision['metrics']['blue_score']}"
                ),
            })

        # Store in decision history
        self.decision_history.append(decision)

        return decision

    def get_history(self, n=10):
        """Get the last N deliberation decisions."""
        return self.decision_history[-n:]


# ── Helpers ──────────────────────────────────────────────────────────────

def _extract_json(text):
    """Extract JSON from a response that may contain markdown code blocks."""
    import re

    # Try ```json ... ``` block first
    match = re.search(r"```json\s*\n(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try raw JSON object
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None
