package cases

import (
	"context"
	"errors"
	"fmt"
	"time"

	"esm/libs/go-common/contracts"
)

// ErrInvalidReview is returned for an unknown review status.
var ErrInvalidReview = errors.New("status must be approved or rejected")

// Service builds cases from triage results and records analyst reviews.
type Service struct {
	Store    Store
	Unmasker Unmasker
	Now      func() time.Time
}

// FromTriageResult creates the case for a triage result. Redelivered results are ignored.
func (s *Service) FromTriageResult(ctx context.Context, r *contracts.TriageResult) (*Case, error) {
	m, err := s.Unmasker.ReverseMap(ctx, r.IncidentID)
	if err != nil {
		return nil, fmt.Errorf("reverse map: %w", err)
	}
	c := Build(r, m, s.Now())
	if err := s.Store.Create(ctx, c); err != nil {
		if errors.Is(err, ErrExists) {
			return c, nil
		}
		return nil, err
	}
	return c, nil
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

// Review records an analyst decision. Only humans change review state (CLAUDE.md §1).
func (s *Service) Review(ctx context.Context, id string, rv Review) (*Case, error) {
	if rv.Status != ReviewApproved && rv.Status != ReviewRejected {
		return nil, ErrInvalidReview
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
	return c, nil
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
