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
