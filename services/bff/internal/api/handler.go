// Package api is the analyst-facing API. It holds no business logic: case reads and reviews
// are forwarded to case-service.
package api

import (
	"encoding/json"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
)

// Handler routes:
//
//	GET  /healthz
//	GET  /api/cases[?review_status=pending]  -> case-service GET /cases
//	GET  /api/cases/{id}                     -> case-service GET /cases/{id}
//	POST /api/cases/{id}/review              -> case-service POST /cases/{id}/review
func Handler(caseService *url.URL) http.Handler {
	proxy := httputil.NewSingleHostReverseProxy(caseService)
	forward := func(w http.ResponseWriter, r *http.Request) {
		r.URL.Path = strings.TrimPrefix(r.URL.Path, "/api")
		r.Host = caseService.Host
		proxy.ServeHTTP(w, r)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})
	mux.HandleFunc("GET /api/cases", forward)
	mux.HandleFunc("GET /api/cases/{id}", forward)
	mux.HandleFunc("POST /api/cases/{id}/review", forward)
	return securityHeaders(mux)
}

// securityHeaders sets response headers for a JSON API that browsers must not sniff, frame or
// share cross-origin (found by the DAST scan in the pipeline).
func securityHeaders(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		h := w.Header()
		h.Set("X-Content-Type-Options", "nosniff")
		h.Set("Cross-Origin-Resource-Policy", "same-origin")
		h.Set("X-Frame-Options", "DENY")
		h.Set("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
		h.Set("Cache-Control", "no-store")
		next.ServeHTTP(w, r)
	})
}
