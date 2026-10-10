package cases

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"time"
	"unicode"

	"esm/libs/go-common/contracts"
)

// ErrInvalidReview is returned for an unknown review status.
var ErrInvalidReview = errors.New("status must be approved or rejected")

// ErrInvalidAnalyst is returned for an analyst name that is too long or has control characters.
var ErrInvalidAnalyst = errors.New("analyst must be at most 128 printable characters")

const maxAnalystLen = 128

// Publisher sends case events to outbound integrations (esm.case-events).
type Publisher interface {
	Publish(ctx context.Context, subject, msgID string, v any) error
}

// Service builds cases from triage results and records analyst reviews.
type Service struct {
	Store    Store
	Unmasker Unmasker
	Events   Publisher // optional
	Now      func() time.Time
	Log      *slog.Logger
}

// FromTriageResult creates the case for a triage result and announces it.
// Redelivered results do not overwrite the stored case; the event is published again with the
// same message ID, so JetStream drops it if the first publish already went through.
func (s *Service) FromTriageResult(ctx context.Context, r *contracts.TriageResult) (*Case, error) {
	m, err := s.Unmasker.ReverseMap(ctx, r.IncidentID)
	if err != nil {
		return nil, fmt.Errorf("reverse map: %w", err)
	}
	c := Build(r, m, s.Now())
	if err := s.Store.Create(ctx, c); err != nil && !errors.Is(err, ErrExists) {
		return nil, err
	} else if errors.Is(err, ErrExists) {
		if c, err = s.Store.Get(ctx, c.ID); err != nil {
			return nil, err
		}
	}
	if err := s.publish(ctx, contracts.CaseEventCreated, "created:"+c.ID, c); err != nil {
		return nil, fmt.Errorf("publish case event: %w", err)
	}
	return c, nil
}

func (s *Service) publish(ctx context.Context, event, msgID string, c *Case) error {
	if s.Events == nil {
		return nil
	}
	return s.Events.Publish(ctx, contracts.SubjectCaseEvents, msgID,
		contracts.CaseEvent{Event: event, CaseID: c.ID, Case: c})
}

// Build assembles a case from a triage result and the incident's reverse map (pure function).
func Build(r *contracts.TriageResult, m map[string]string, now time.Time) *Case {
	inc := r.Incident
	c := &Case{
		ID:              r.IncidentID,
		IncidentID:      r.IncidentID,
		CreatedAt:       now,
		UpdatedAt:       now,
		TriageStatus:    r.Status,
		TriageError:     r.Error,
		ReviewStatus:    ReviewPending,
		RiskScore:       inc.RiskScore,
		AlertCount:      inc.AlertCount,
		IncidentSummary: unmaskText(inc.Summary, m),
		MITRETechniques: inc.MITRETechniques,
		AffectedHosts:   unmaskAll(inc.AffectedHosts, m),
		AffectedUsers:   unmaskAll(inc.AffectedUsers, m),
		Severity:        severityFromRisk(inc.RiskScore),
	}
	for _, ip := range inc.SourceIPs {
		c.SourceIPs = append(c.SourceIPs, unmaskText(ip.Token, m))
	}
	for _, e := range inc.Timeline {
		e.Host = unmaskText(e.Host, m)
		e.User = unmaskText(e.User, m)
		c.Timeline = append(c.Timeline, e)
	}

	if d := r.Decision; d != nil {
		c.Severity = d.SeveritySuggestion
		c.Summary = unmaskText(d.Summary, m)
		c.Rationale = unmaskText(d.Rationale, m)
		c.RecommendedActions = unmaskAll(d.RecommendedActions, m)
		c.Confidence = d.Confidence
		c.FalsePositiveLikelihood = d.FalsePositiveLikelihood
		c.ModelID = d.ModelID
		c.PromptHash = d.PromptHash
		if len(d.MITRETechniquesConfirmed) > 0 {
			c.MITRETechniques = d.MITRETechniquesConfirmed
		}
	} else {
		c.Summary = "Not triaged by the LLM (" + r.Status + "); needs analyst triage. " + c.IncidentSummary
	}
	return c
}

// Review records an analyst decision. Only humans change review state (design rule 1, ROADMAP.md).
func (s *Service) Review(ctx context.Context, id string, rv Review) (*Case, error) {
	if rv.Status != ReviewApproved && rv.Status != ReviewRejected {
		return nil, ErrInvalidReview
	}
	if !validAnalyst(rv.Analyst) {
		return nil, ErrInvalidAnalyst
	}
	c, err := s.Store.Get(ctx, id)
	if err != nil {
		return nil, err
	}
	now := s.Now()
	c.ReviewStatus = rv.Status
	c.ReviewedBy = rv.Analyst
	c.ReviewedAt = &now
	c.AnalystNotes = rv.Notes
	c.UpdatedAt = now
	if err := s.Store.Put(ctx, c); err != nil {
		return nil, err
	}
	// The review is stored either way; a failed publish only delays ticketing, so report it in the
	// log instead of failing the analyst's request.
	msgID := fmt.Sprintf("reviewed:%s:%d", c.ID, now.UnixNano())
	if err := s.publish(ctx, contracts.CaseEventReviewed, msgID, c); err != nil && s.Log != nil {
		s.Log.Error("case event publish failed", "case_id", c.ID, "error", err)
	}
	// The stored case already holds the unmasked identifiers, so the reverse map is no longer
	// needed (design rule 3). masking-service purges leftover maps after its TTL.
	if err := s.Unmasker.DeleteMap(ctx, c.IncidentID); err != nil && s.Log != nil {
		s.Log.Warn("reverse map delete failed", "incident_id", c.IncidentID, "error", err)
	}
	return c, nil
}

func validAnalyst(s string) bool {
	if len([]rune(s)) > maxAnalystLen {
		return false
	}
	for _, r := range s {
		if unicode.IsControl(r) {
			return false
		}
	}
	return true
}

func severityFromRisk(risk int) string {
	switch {
	case risk >= 75:
		return "critical"
	case risk >= 50:
		return "high"
	case risk >= 25:
		return "medium"
	default:
		return "low"
	}
}
