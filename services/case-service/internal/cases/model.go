// Package cases turns triage results into analyst cases and manages their review state.
package cases

import (
	"time"

	"esm/libs/go-common/contracts"
)

// Review states. Every case starts pending; only an analyst moves it.
const (
	ReviewPending  = "pending"
	ReviewApproved = "approved"
	ReviewRejected = "rejected"
)

// Case is the analyst-facing record stored in the esm-cases index. Identifiers are un-masked.
type Case struct {
	ID         string    `json:"id"`
	IncidentID string    `json:"incident_id"`
	CreatedAt  time.Time `json:"created_at"`
	UpdatedAt  time.Time `json:"updated_at"`

	// TriageStatus is "triaged", "budget_exceeded" or "llm_failed" (contracts.TriageStatus*).
	TriageStatus string `json:"triage_status"`
	TriageError  string `json:"triage_error,omitempty"`

	ReviewStatus string     `json:"review_status"`
	ReviewedBy   string     `json:"reviewed_by,omitempty"`
	ReviewedAt   *time.Time `json:"reviewed_at,omitempty"`
	AnalystNotes string     `json:"analyst_notes,omitempty"`

	Severity                string   `json:"severity"`
	RiskScore               int      `json:"risk_score"`
	AlertCount              int      `json:"alert_count"`
	Summary                 string   `json:"summary"`
	IncidentSummary         string   `json:"incident_summary"`
	RecommendedActions      []string `json:"recommended_actions,omitempty"`
	Rationale               string   `json:"rationale,omitempty"`
	Confidence              float64  `json:"confidence,omitempty"`
	FalsePositiveLikelihood float64  `json:"false_positive_likelihood,omitempty"`
	MITRETechniques         []string `json:"mitre_techniques"`

	AffectedHosts []string                  `json:"affected_hosts"`
	AffectedUsers []string                  `json:"affected_users"`
	SourceIPs     []string                  `json:"source_ips"`
	Timeline      []contracts.TimelineEntry `json:"timeline"`

	ModelID    string `json:"model_id,omitempty"`
	PromptHash string `json:"prompt_hash,omitempty"`
}

// Review is the analyst decision submitted through the API.
type Review struct {
	Status  string `json:"status"`
	Analyst string `json:"analyst"`
	Notes   string `json:"notes"`
}
