// Package contracts defines the messages exchanged between platform services.
// The Python side mirrors these in libs/py-common/esm_common/contracts.py; keep both in sync.
package contracts

import "time"

// Bus subjects (ADR-013, ADR-017).
const (
	SubjectAlerts          = "esm.alerts"           // detection-service -> alert-gateway
	SubjectIncidents       = "esm.incidents"        // alert-gateway -> enrichment-service
	SubjectMaskedIncidents = "esm.masked-incidents" // enrichment-service -> llm-orchestrator
	SubjectTriageResults   = "esm.triage-decisions" // llm-orchestrator -> case-service
	SubjectDLQ             = "esm.dlq"              // messages that failed MaxDeliver times
)

// Alert is a normalized Kibana Security alert, published by detection-service.
type Alert struct {
	ID                  string            `json:"id"`
	Timestamp           time.Time         `json:"timestamp"`
	RuleID              string            `json:"rule_id"`
	RuleName            string            `json:"rule_name"`
	Severity            string            `json:"severity"`
	MITRETechniqueIDs   []string          `json:"mitre_technique_ids"`
	MITRETechniqueNames []string          `json:"mitre_technique_names"`
	HostName            string            `json:"host_name"`
	UserName            string            `json:"user_name"`
	SourceIP            string            `json:"source_ip,omitempty"`
	ProcessName         string            `json:"process_name,omitempty"`
	EventDetails        map[string]string `json:"event_details,omitempty"`
}

// Incident groups correlated alerts; published by alert-gateway.
type Incident struct {
	ID              string    `json:"id"`
	CreatedAt       time.Time `json:"created_at"`
	UpdatedAt       time.Time `json:"updated_at"`
	Alerts          []*Alert  `json:"alerts"`
	AlertCount      int       `json:"alert_count"`
	AffectedHosts   []string  `json:"affected_hosts"`
	AffectedUsers   []string  `json:"affected_users"`
	SourceIPs       []string  `json:"source_ips"`
	MITRETechniques []string  `json:"mitre_techniques"`
	RiskScore       int       `json:"risk_score"`
	Status          string    `json:"status"`
	CorrelationKey  string    `json:"correlation_key"`
}

// MaskedIP is a pseudonymized address with deterministic enrichment.
type MaskedIP struct {
	Token      string `json:"token"`
	GeoCountry string `json:"geo_country,omitempty"`
	Private    bool   `json:"private"`
}

// TimelineEntry is one alert of a masked incident.
type TimelineEntry struct {
	Timestamp time.Time `json:"timestamp"`
	Rule      string    `json:"rule"`
	Severity  string    `json:"severity"`
	Host      string    `json:"host"`
	User      string    `json:"user"`
}

// MaskedIncident is the curated, pseudonymized incident sent to llm-orchestrator.
// Identifiers are tokens such as host_1a2b3c; plaintext never appears here.
type MaskedIncident struct {
	IncidentID      string          `json:"incident_id"`
	CreatedAt       time.Time       `json:"created_at"`
	Summary         string          `json:"summary"`
	AffectedHosts   []string        `json:"affected_hosts"`
	AffectedUsers   []string        `json:"affected_users"`
	SourceIPs       []MaskedIP      `json:"source_ips"`
	Timeline        []TimelineEntry `json:"timeline"`
	MITRETechniques []string        `json:"mitre_techniques"`
	RiskScore       int             `json:"risk_score"`
	AlertCount      int             `json:"alert_count"`
}

// TriageDecision is the schema-validated LLM suggestion.
type TriageDecision struct {
	IncidentID               string   `json:"incident_id"`
	ModelID                  string   `json:"model_id"`
	SeveritySuggestion       string   `json:"severity_suggestion"`
	MITRETechniquesConfirmed []string `json:"mitre_techniques_confirmed"`
	FalsePositiveLikelihood  float64  `json:"false_positive_likelihood"`
	Summary                  string   `json:"summary"`
	RecommendedActions       []string `json:"recommended_actions"`
	Confidence               float64  `json:"confidence"`
	Rationale                string   `json:"rationale"`
	PromptHash               string   `json:"prompt_hash"`
	InputTokens              int      `json:"input_tokens"`
	OutputTokens             int      `json:"output_tokens"`
	LatencyMS                float64  `json:"latency_ms"`
}

// Triage result statuses.
const (
	TriageStatusTriaged        = "triaged"
	TriageStatusBudgetExceeded = "budget_exceeded"
	TriageStatusLLMFailed      = "llm_failed"
)

// TriageResult is published by llm-orchestrator for every masked incident.
// Decision is nil when the LLM was not called or failed; the incident still becomes a case.
type TriageResult struct {
	IncidentID string          `json:"incident_id"`
	Status     string          `json:"status"`
	Error      string          `json:"error,omitempty"`
	Decision   *TriageDecision `json:"decision"`
	Incident   MaskedIncident  `json:"incident"`
}
