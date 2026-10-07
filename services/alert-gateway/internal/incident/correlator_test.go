package incident

import (
	"testing"
	"time"

	"esm/libs/go-common/contracts"
)

func alert(id, host, user, sev, technique string) *contracts.Alert {
	return &contracts.Alert{ID: id, Timestamp: time.Now(), HostName: host, UserName: user, Severity: sev,
		MITRETechniqueIDs: []string{technique}}
}

func TestThresholdEmitsIncident(t *testing.T) {
	c := NewCorrelator(2, time.Hour)
	if inc := c.Ingest(alert("a1", "h1", "u1", "high", "T1059")); inc != nil {
		t.Fatal("incident emitted before threshold")
	}
	inc := c.Ingest(alert("a2", "h1", "u1", "medium", "T1059"))
	if inc == nil {
		t.Fatal("expected incident at threshold")
	}
	if inc.AlertCount != 2 || inc.RiskScore != 35 || inc.Status != StatusPendingTriage {
		t.Fatalf("unexpected incident: count=%d risk=%d status=%s", inc.AlertCount, inc.RiskScore, inc.Status)
	}
}

func TestDifferentKeysAreSeparate(t *testing.T) {
	c := NewCorrelator(2, time.Hour)
	c.Ingest(alert("a1", "h1", "u1", "high", "T1059"))
	if inc := c.Ingest(alert("a2", "h2", "u1", "high", "T1059")); inc != nil {
		t.Fatal("alerts on different hosts must not be correlated")
	}
}

func TestDuplicateAlertIgnored(t *testing.T) {
	c := NewCorrelator(2, time.Hour)
	c.Ingest(alert("a1", "h1", "u1", "high", "T1059"))
	if inc := c.Ingest(alert("a1", "h1", "u1", "high", "T1059")); inc != nil {
		t.Fatal("redelivered alert must not count twice")
	}
}

func TestFlushAfterWindow(t *testing.T) {
	now := time.Now()
	c := NewCorrelator(10, time.Minute)
	c.now = func() time.Time { return now }
	c.Ingest(alert("a1", "h1", "u1", "low", "T1110"))
	if got := c.Flush(); len(got) != 0 {
		t.Fatal("flushed before the window expired")
	}
	now = now.Add(2 * time.Minute)
	got := c.Flush()
	if len(got) != 1 || got[0].AlertCount != 1 || got[0].Status != StatusPendingTriage {
		t.Fatalf("expected one pending incident, got %+v", got)
	}
}

func TestRiskScoreCapped(t *testing.T) {
	c := NewCorrelator(5, time.Hour)
	var inc *contracts.Incident
	for i, id := range []string{"a1", "a2", "a3", "a4", "a5"} {
		inc = c.Ingest(alert(id, "h1", "u1", "critical", "T1003"))
		_ = i
	}
	if inc == nil || inc.RiskScore != 100 {
		t.Fatalf("risk score should cap at 100, got %+v", inc)
	}
}

func TestAddUniqueSortedAndSkipsEmpty(t *testing.T) {
	var s []string
	for _, v := range []string{"b", "a", "", "b", "c"} {
		s = addUnique(s, v)
	}
	if len(s) != 3 || s[0] != "a" || s[1] != "b" || s[2] != "c" {
		t.Fatalf("got %v", s)
	}
}
