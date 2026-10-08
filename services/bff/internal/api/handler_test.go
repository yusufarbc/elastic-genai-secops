package api

import (
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
)

func TestForwardsCaseRoutes(t *testing.T) {
	var gotPath, gotMethod string
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath, gotMethod = r.URL.RequestURI(), r.Method
		_, _ = io.WriteString(w, `{"ok":true}`)
	}))
	defer backend.Close()
	u, _ := url.Parse(backend.URL)
	h := Handler(u)

	cases := []struct{ method, path, wantPath string }{
		{"GET", "/api/cases?review_status=pending", "/cases?review_status=pending"},
		{"GET", "/api/cases/inc-1", "/cases/inc-1"},
		{"POST", "/api/cases/inc-1/review", "/cases/inc-1/review"},
	}
	for _, c := range cases {
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, httptest.NewRequest(c.method, c.path, nil))
		if rec.Code != http.StatusOK || gotPath != c.wantPath || gotMethod != c.method {
			t.Errorf("%s %s -> backend %s %s (status %d)", c.method, c.path, gotMethod, gotPath, rec.Code)
		}
	}

	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest("DELETE", "/api/cases/inc-1", nil))
	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("DELETE should not be routed, got %d", rec.Code)
	}
}

func TestSecurityHeaders(t *testing.T) {
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = io.WriteString(w, `{"cases":[]}`)
	}))
	defer backend.Close()
	u, _ := url.Parse(backend.URL)
	h := Handler(u)

	for _, path := range []string{"/healthz", "/api/cases"} {
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, httptest.NewRequest("GET", path, nil))
		for k, want := range map[string]string{
			"X-Content-Type-Options":       "nosniff",
			"Cross-Origin-Resource-Policy": "same-origin",
			"Cache-Control":                "no-store",
		} {
			if got := rec.Header().Get(k); got != want {
				t.Errorf("%s: %s = %q, want %q", path, k, got, want)
			}
		}
	}
}
