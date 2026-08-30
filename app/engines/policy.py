from typing import Literal

# Predefined policy profiles per use-case
POLICY_PROFILES = {
    "customer_facing": {
        "name": "Customer-Facing Chatbot",
        "description": "Real-time, user-visible responses. Low latency budget. Hard blocks on PII. Strict bias filter.",
        "risk_tolerance": "low",
        "latency_budget_ms": 30,
        "pii_detection": True,
        "hallucination_check": True,
        "bias_filter": True,
        "on_pii": "block",
        "on_hallucination": "redact",
        "on_bias": "block",
        "audit_trail": True,
    },
    "internal_copilot": {
        "name": "Internal Employee Copilot",
        "description": "Internal tooling for employees. Medium risk tolerance. Escalate for human review instead of hard blocking.",
        "risk_tolerance": "medium",
        "latency_budget_ms": 100,
        "pii_detection": True,
        "hallucination_check": True,
        "bias_filter": True,
        "on_pii": "redact",
        "on_hallucination": "flag",
        "on_bias": "escalate",
        "audit_trail": True,
    },
    "batch_processing": {
        "name": "Batch / Offline Processing",
        "description": "No real-time latency constraint. Full deep-scan enabled. All violations logged for post-hoc audit.",
        "risk_tolerance": "high",
        "latency_budget_ms": 500,
        "pii_detection": True,
        "hallucination_check": True,
        "bias_filter": True,
        "on_pii": "redact",
        "on_hallucination": "redact",
        "on_bias": "flag",
        "audit_trail": True,
    },
}


class PolicyEngine:
    """
    Singleton policy engine. Stores the active governance profile and
    individual module overrides. All other engines read from this at runtime.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialised = False
        return cls._instance

    def __init__(self):
        if self._initialised:
            return
        self.active_profile_key: str = "customer_facing"
        self.overrides: dict = {}
        self._initialised = True

    @property
    def active_policy(self) -> dict:
        base = POLICY_PROFILES[self.active_profile_key].copy()
        base.update(self.overrides)
        return base

    def set_profile(self, profile_key: str, overrides: dict = None):
        if profile_key not in POLICY_PROFILES:
            raise ValueError(f"Unknown profile: {profile_key}")
        self.active_profile_key = profile_key
        self.overrides = overrides or {}

    def get_all_profiles(self) -> dict:
        return POLICY_PROFILES

    def get_status(self) -> dict:
        return {
            "active_profile": self.active_profile_key,
            "policy": self.active_policy,
            "available_profiles": list(POLICY_PROFILES.keys()),
        }
