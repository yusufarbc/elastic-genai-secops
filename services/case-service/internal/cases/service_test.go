package cases

import (
	"context"
	"testing"
	"time"

	"esm/libs/go-common/contracts"
)

var reverseMap = map[string]string{
	"host_1a2b3c": "PC-LAB-01",
	"user_4d5e6f": "alice",
	"ip_abcdef":   "10.1.1.50",
}

func triageResult(decision *contracts.TriageDecision, status string) *contracts.TriageResult {
	return &contracts.TriageResult{
		IncidentID: "inc-1",
		Status:     status,
		Decision:   decision,
		Incident: contracts.MaskedIncident{
			IncidentID:      "inc-1",
			Summary:         "1 alert(s) on host_1a2b3c",
			AffectedHosts:   []string{"host_1a2b3c"},
			AffectedUsers:   []string{"user_4d5e6f"},
			SourceIPs:       []contracts.MaskedIP{{Token: "ip_abcdef", Private: true}},
			Timeline:        []contracts.TimelineEntry{{Rule: "WIN-001", Host: "host_1a2b3c", User: "user_4d5e6f"}},
			MITRETechniques: []string{"T1059"},
			RiskScore:       60,
			AlertCount:      1,
		},
	}
}

func TestBuildUnmasksDecision(t *testing.T) {
	d := &contracts.TriageDecision{
		SeveritySuggestion: "high",
		Summary:            "Macro on host_1a2b3c run by user_4d5e6f",
		RecommendedActions: []string{"Isolate host_1a2b3c", "Check unknown token host_ffffff"},
		Confidence:         0.8,
	}
	c := Build(triageResult(d, contracts.TriageStatusTriaged), reverseMap, time.Unix(0, 0))

	if c.Summary != "Macro on PC-LAB-01 run by alice" {
		t.Errorf("summary = %q", c.Summary)
	}
	if c.RecommendedActions[0] != "Isolate PC-LAB-01" || c.RecommendedActions[1] != "Check unknown token host_ffffff" {
		t.Errorf("actions = %v", c.RecommendedActions)
	}
	if c.AffectedHosts[0] != "PC-LAB-01" || c.AffectedUsers[0] != "alice" || c.SourceIPs[0] != "10.1.1.50" {
		t.Errorf("identifiers not unmasked: %+v", c)
	}
	if c.Timeline[0].Host != "PC-LAB-01" || c.Severity != "high" || c.ReviewStatus != ReviewPending {
		t.Errorf("unexpected case: %+v", c)
	}
}

func TestBuildWithoutDecisionNeedsAnalyst(t *testing.T) {
	c := Build(triageResult(nil, contracts.TriageStatusBudgetExceeded), reverseMap, time.Unix(0, 0))
	if c.Severity != "high" { // risk 60
		t.Errorf("severity from risk = %q", c.Severity)
	}
	if c.TriageStatus != contracts.TriageStatusBudgetExceeded || c.Summary == "" {
		t.Errorf("unexpected case: %+v", c)
	}
}

type memStore struct{ m map[string]*Case }

func (s *memStore) Create(_ context.Context, c *Case) error {
	if _, ok := s.m[c.ID]; ok {
		return ErrExists
	}
	s.m[c.ID] = c
	return nil
}
func (s *memStore) Put(_ context.Context, c *Case) error { s.m[c.ID] = c; return nil }
func (s *memStore) Get(_ context.Context, id string) (*Case, error) {
	if c, ok := s.m[id]; ok {
		return c, nil
	}
	return nil, ErrNotFound
}
func (s *memStore) List(context.Context, string, int) ([]*Case, error) { return nil, nil }

type recordedEvent struct{ subject, msgID, event string }

type fakePublisher struct{ events []recordedEvent }

func (p *fakePublisher) Publish(_ context.Context, subject, msgID string, v any) error {
	p.events = append(p.events, recordedEvent{subject, msgID, v.(contracts.CaseEvent).Event})
	return nil
}

type mapUnmasker struct {
	m       map[string]string
	deleted []string
}

func (u *mapUnmasker) ReverseMap(context.Context, string) (map[string]string, error) {
	return u.m, nil
}
func (u *mapUnmasker) DeleteMap(_ context.Context, id string) error {
	u.deleted = append(u.deleted, id)
	return nil
}

func TestReviewFlowAndRedelivery(t *testing.T) {
	store := &memStore{m: map[string]*Case{}}
	pub := &fakePublisher{}
	unmasker := &mapUnmasker{m: reverseMap}
	svc := &Service{Store: store, Unmasker: unmasker, Events: pub, Now: time.Now}
	defer func() {
		// created, reviewed, then created again (same ID, JetStream drops the duplicate)
		want := []string{"created:inc-1", "reviewed:", "created:inc-1"}
		if len(pub.events) != len(want) {
			t.Fatalf("events = %+v", pub.events)
		}
		for i, e := range pub.events {
			if e.subject != contracts.SubjectCaseEvents || len(e.msgID) < len(want[i]) || e.msgID[:len(want[i])] != want[i] {
				t.Errorf("event %d = %+v, want msgID prefix %q", i, e, want[i])
			}
		}
	}()
	ctx := context.Background()

	if _, err := svc.FromTriageResult(ctx, triageResult(nil, contracts.TriageStatusLLMFailed)); err != nil {
		t.Fatal(err)
	}
	if _, err := svc.Review(ctx, "inc-1", Review{Status: "maybe"}); err != ErrInvalidReview {
		t.Fatalf("expected ErrInvalidReview, got %v", err)
	}
	if len(unmasker.deleted) != 0 {
		t.Fatalf("map deleted before review: %v", unmasker.deleted)
	}
	if _, err := svc.Review(ctx, "inc-1", Review{Status: ReviewApproved, Analyst: "bob"}); err != nil {
		t.Fatal(err)
	}
	if len(unmasker.deleted) != 1 || unmasker.deleted[0] != "inc-1" {
		t.Fatalf("reverse map not deleted after review: %v", unmasker.deleted)
	}
	// A redelivered triage result must not reset the review.
	if _, err := svc.FromTriageResult(ctx, triageResult(nil, contracts.TriageStatusLLMFailed)); err != nil {
		t.Fatal(err)
	}
	if got := store.m["inc-1"]; got.ReviewStatus != ReviewApproved || got.ReviewedBy != "bob" {
		t.Fatalf("review lost: %+v", got)
	}
}
