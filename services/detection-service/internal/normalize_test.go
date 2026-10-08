package internal

import (
	"encoding/json"
	"reflect"
	"testing"
)

// A trimmed Kibana 8.13 alert document: kibana.* keys are dotted, event fields are nested.
const sampleAlert = `{
  "@timestamp": "2026-10-07T18:40:12.372Z",
  "kibana.alert.uuid": "abc",
  "kibana.alert.severity": "high",
  "kibana.alert.rule.rule_id": "esm-win-001",
  "kibana.alert.rule.name": "[WIN-001] Office application spawned a command or script interpreter",
  "kibana.alert.rule.threat": [
    {"tactic": {"id": "TA0002"}, "technique": [
      {"id": "T1059", "name": "Command and Scripting Interpreter",
       "subtechnique": [{"id": "T1059.001", "name": "PowerShell"}]}
    ]}
  ],
  "host": {"name": "PC-LAB-01"},
  "user": {"name": "alice"},
  "process": {"name": "powershell.exe", "command_line": "powershell -enc AAA", "parent": {"name": "WINWORD.EXE"}},
  "event": {"code": "1"}
}`

func TestNormalize(t *testing.T) {
	var src map[string]any
	if err := json.Unmarshal([]byte(sampleAlert), &src); err != nil {
		t.Fatal(err)
	}
	a := Normalize("alert-1", src)

	if a.RuleID != "esm-win-001" || a.Severity != "high" || a.HostName != "PC-LAB-01" || a.UserName != "alice" {
		t.Fatalf("unexpected alert: %+v", a)
	}
	if a.Timestamp.IsZero() || a.Timestamp.Year() != 2026 {
		t.Fatalf("timestamp not parsed: %v", a.Timestamp)
	}
	if want := []string{"T1059", "T1059.001"}; !reflect.DeepEqual(a.MITRETechniqueIDs, want) {
		t.Fatalf("techniques = %v, want %v", a.MITRETechniqueIDs, want)
	}
	if a.EventDetails["process.parent.name"] != "WINWORD.EXE" || a.EventDetails["event.code"] != "1" {
		t.Fatalf("event details = %v", a.EventDetails)
	}
}

func TestLookupDottedAndNested(t *testing.T) {
	src := map[string]any{
		"host.name":    "dotted",
		"source":       map[string]any{"ip": "10.0.0.1"},
		"kibana.alert": map[string]any{"severity": "low"},
		"tags":         []any{"first", "second"},
		"destination":  map[string]any{"port": float64(3389)},
	}
	cases := map[string]string{
		"host.name":             "dotted",
		"source.ip":             "10.0.0.1",
		"kibana.alert.severity": "low",
		"tags":                  "first",
		"destination.port":      "3389",
		"missing.field":         "",
	}
	for path, want := range cases {
		if got := str(src, path); got != want {
			t.Errorf("str(%q) = %q, want %q", path, got, want)
		}
	}
}

func TestNormalizeUnknownSeverity(t *testing.T) {
	a := Normalize("x", map[string]any{"kibana.alert.severity": "bogus"})
	if a.Severity != "medium" {
		t.Fatalf("severity = %q, want medium", a.Severity)
	}
}
