// Package incident groups related alerts into incidents (the only place incidents are formed).
package incident

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"sort"
	"sync"
	"time"

	"esm/libs/go-common/contracts"
)

// Incident statuses.
const (
	StatusNew           = "new"
	StatusPendingTriage = "pending_triage"
)

// severityWeight maps severity to its contribution to the risk score.
var severityWeight = map[string]int{
	"critical": 40,
	"high":     25,
	"medium":   10,
	"low":      3,
}

// Correlator groups alerts by (host, user, first MITRE technique) inside a time window.
// An incident is emitted when it reaches the alert threshold or its window expires.
type Correlator struct {
	mu        sync.Mutex
	buckets   map[string]*bucket
	threshold int
	window    time.Duration
	now       func() time.Time
}

type bucket struct {
	inc       *contracts.Incident
	expiresAt time.Time
}

// NewCorrelator returns a Correlator. threshold < 1 is treated as 1.
func NewCorrelator(threshold int, window time.Duration) *Correlator {
	if threshold < 1 {
		threshold = 1
	}
	return &Correlator{buckets: map[string]*bucket{}, threshold: threshold, window: window, now: time.Now}
}

// Ingest adds an alert and returns the incident if it is complete, otherwise nil.
func (c *Correlator) Ingest(a *contracts.Alert) *contracts.Incident {
	key := correlationKey(a)
	c.mu.Lock()
	defer c.mu.Unlock()

	b, ok := c.buckets[key]
	if !ok {
		b = &bucket{
			inc: &contracts.Incident{
				ID:             newID(),
				CreatedAt:      a.Timestamp,
				Status:         StatusNew,
				CorrelationKey: key,
			},
			expiresAt: c.now().Add(c.window),
		}
		c.buckets[key] = b
	}
	inc := b.inc
	for _, existing := range inc.Alerts {
		if existing.ID == a.ID {
			return nil // redelivered alert
		}
	}
	inc.Alerts = append(inc.Alerts, a)
	inc.AlertCount = len(inc.Alerts)
	if a.Timestamp.After(inc.UpdatedAt) {
		inc.UpdatedAt = a.Timestamp
	}
	if a.Timestamp.Before(inc.CreatedAt) {
		inc.CreatedAt = a.Timestamp
	}
	merge(inc, a)
	inc.RiskScore = riskScore(inc)

	if inc.AlertCount >= c.threshold || c.now().After(b.expiresAt) {
		delete(c.buckets, key)
		inc.Status = StatusPendingTriage
		return inc
	}
	return nil
}

// Flush returns and removes every incident whose window has expired.
func (c *Correlator) Flush() []*contracts.Incident {
	c.mu.Lock()
	defer c.mu.Unlock()
	now := c.now()
	var out []*contracts.Incident
	for key, b := range c.buckets {
		if now.After(b.expiresAt) {
			b.inc.Status = StatusPendingTriage
			out = append(out, b.inc)
			delete(c.buckets, key)
		}
	}
	return out
}

func correlationKey(a *contracts.Alert) string {
	technique := ""
	if len(a.MITRETechniqueIDs) > 0 {
		technique = a.MITRETechniqueIDs[0]
	}
	return fmt.Sprintf("%s|%s|%s", a.HostName, a.UserName, technique)
}

func merge(inc *contracts.Incident, a *contracts.Alert) {
	inc.AffectedHosts = addUnique(inc.AffectedHosts, a.HostName)
	inc.AffectedUsers = addUnique(inc.AffectedUsers, a.UserName)
	inc.SourceIPs = addUnique(inc.SourceIPs, a.SourceIP)
	for _, t := range a.MITRETechniqueIDs {
		inc.MITRETechniques = addUnique(inc.MITRETechniques, t)
	}
}

func riskScore(inc *contracts.Incident) int {
	score := 0
	for _, a := range inc.Alerts {
		score += severityWeight[a.Severity]
	}
	if n := len(inc.AffectedHosts); n > 1 {
		score += (n - 1) * 5
	}
	if n := len(inc.MITRETechniques); n > 1 {
		score += (n - 1) * 3
	}
	if score > 100 {
		score = 100
	}
	return score
}

// addUnique appends v (if non-empty and not present) and keeps the slice sorted.
func addUnique(ss []string, v string) []string {
	if v == "" {
		return ss
	}
	i := sort.SearchStrings(ss, v)
	if i < len(ss) && ss[i] == v {
		return ss
	}
	ss = append(ss, "")
	copy(ss[i+1:], ss[i:])
	ss[i] = v
	return ss
}

func newID() string {
	b := make([]byte, 12)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	return "inc-" + hex.EncodeToString(b)
}
