"""Messages exchanged between platform services.

Mirrors libs/go-common/contracts/contracts.go; keep both in sync.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

SUBJECT_ALERTS = "esm.alerts"
SUBJECT_INCIDENTS = "esm.incidents"
SUBJECT_MASKED_INCIDENTS = "esm.masked-incidents"
SUBJECT_TRIAGE_RESULTS = "esm.triage-decisions"
SUBJECT_DLQ = "esm.dlq"

TRIAGE_STATUS_TRIAGED = "triaged"
TRIAGE_STATUS_BUDGET_EXCEEDED = "budget_exceeded"
TRIAGE_STATUS_LLM_FAILED = "llm_failed"


class Alert(BaseModel):
    id: str
    timestamp: datetime
    rule_id: str = ""
    rule_name: str = ""
    severity: str = "medium"
    mitre_technique_ids: list[str] | None = None
    mitre_technique_names: list[str] | None = None
    host_name: str = ""
    user_name: str = ""
    source_ip: str | None = None
    process_name: str | None = None
    event_details: dict[str, str] | None = None


class Incident(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    alerts: list[Alert]
    alert_count: int
    affected_hosts: list[str] | None = None
    affected_users: list[str] | None = None
    source_ips: list[str] | None = None
    mitre_techniques: list[str] | None = None
    risk_score: int = 0
    status: str = "pending_triage"
    correlation_key: str = ""


class MaskedIP(BaseModel):
    token: str
    geo_country: str | None = None
    private: bool = False


class TimelineEntry(BaseModel):
    timestamp: datetime
    rule: str
    severity: str
    host: str
    user: str


class MaskedIncident(BaseModel):
    """Curated, pseudonymized incident: the only incident data that reaches the LLM."""

    incident_id: str
    created_at: datetime
    summary: str
    affected_hosts: list[str] = Field(default_factory=list)
    affected_users: list[str] = Field(default_factory=list)
    source_ips: list[MaskedIP] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    mitre_techniques: list[str] = Field(default_factory=list)
    risk_score: int = 0
    alert_count: int = 0


class TriageDecision(BaseModel):
    """Schema-validated LLM suggestion. Never an action trigger (CLAUDE.md section 6)."""

    incident_id: str
    model_id: str
    severity_suggestion: str = Field(pattern="^(critical|high|medium|low)$")
    mitre_techniques_confirmed: list[str]
    false_positive_likelihood: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=1, max_length=4000)
    recommended_actions: list[str] = Field(max_length=20)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(max_length=4000)
    prompt_hash: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


class TriageResult(BaseModel):
    """Published for every masked incident; decision is None when the LLM was not used."""

    incident_id: str
    status: str
    error: str = ""
    decision: TriageDecision | None = None
    incident: MaskedIncident
