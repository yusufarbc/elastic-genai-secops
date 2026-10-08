package internal

import (
	"fmt"
	"strings"
	"time"

	"esm/libs/go-common/contracts"
)

// detailFields are copied from the alert document into Alert.EventDetails when present.
var detailFields = []string{
	"event.code", "event.action", "process.command_line", "process.parent.name",
	"destination.ip", "destination.port", "destination.geo.country_iso_code", "registry.path",
}

// Normalize converts a Kibana Security alert document (.alerts-security.alerts-*) into an Alert.
// Alert documents mix dotted keys ("kibana.alert.rule.name") and nested objects ("host": {"name": ...}),
// so every lookup accepts both shapes.
func Normalize(id string, src map[string]any) *contracts.Alert {
	ts := time.Now().UTC()
	if raw := str(src, "@timestamp"); raw != "" {
		if parsed, err := time.Parse(time.RFC3339Nano, raw); err == nil {
			ts = parsed
		}
	}

	severity := strings.ToLower(str(src, "kibana.alert.severity"))
	switch severity {
	case "critical", "high", "medium", "low":
	default:
		severity = "medium"
	}

	a := &contracts.Alert{
		ID:          id,
		Timestamp:   ts,
		RuleID:      str(src, "kibana.alert.rule.rule_id"),
		RuleName:    str(src, "kibana.alert.rule.name"),
		Severity:    severity,
		HostName:    str(src, "host.name"),
		UserName:    str(src, "user.name"),
		SourceIP:    str(src, "source.ip"),
		ProcessName: str(src, "process.name"),
	}
	a.MITRETechniqueIDs, a.MITRETechniqueNames = techniques(lookup(src, "kibana.alert.rule.threat"))

	for _, f := range detailFields {
		if v := str(src, f); v != "" {
			if a.EventDetails == nil {
				a.EventDetails = map[string]string{}
			}
			a.EventDetails[f] = v
		}
	}
	return a
}

// techniques extracts technique and sub-technique IDs/names from kibana.alert.rule.threat.
func techniques(threat any) (ids, names []string) {
	seen := map[string]bool{}
	add := func(m map[string]any) {
		id, _ := m["id"].(string)
		if id == "" || seen[id] {
			return
		}
		seen[id] = true
		name, _ := m["name"].(string)
		ids = append(ids, id)
		names = append(names, name)
	}
	for _, t := range asSlice(threat) {
		tm, _ := t.(map[string]any)
		for _, tech := range asSlice(tm["technique"]) {
			techMap, _ := tech.(map[string]any)
			if techMap == nil {
				continue
			}
			add(techMap)
			for _, sub := range asSlice(techMap["subtechnique"]) {
				if sm, ok := sub.(map[string]any); ok {
					add(sm)
				}
			}
		}
	}
	return ids, names
}

// lookup resolves a dotted path, trying the literal dotted key first and then nested objects
// (including partially dotted forms such as {"host": {"name": ...}} or {"kibana.alert": {...}}).
func lookup(m map[string]any, path string) any {
	if v, ok := m[path]; ok {
		return v
	}
	parts := strings.Split(path, ".")
	for i := len(parts) - 1; i >= 1; i-- {
		head := strings.Join(parts[:i], ".")
		if child, ok := m[head].(map[string]any); ok {
			if v := lookup(child, strings.Join(parts[i:], ".")); v != nil {
				return v
			}
		}
	}
	return nil
}

// str returns the value at path as a string; arrays yield their first element.
func str(m map[string]any, path string) string {
	v := lookup(m, path)
	if s := asSlice(v); len(s) > 0 {
		v = s[0]
	}
	switch t := v.(type) {
	case nil:
		return ""
	case string:
		return t
	case float64:
		if t == float64(int64(t)) {
			return fmt.Sprintf("%d", int64(t))
		}
		return fmt.Sprintf("%g", t)
	default:
		return fmt.Sprint(t)
	}
}

func asSlice(v any) []any {
	s, _ := v.([]any)
	return s
}
