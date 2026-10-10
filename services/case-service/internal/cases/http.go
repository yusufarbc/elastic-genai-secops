package cases

import (
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
)

// Handler exposes the case API:
//
//	GET  /healthz
//	GET  /cases?review_status=pending&size=50
//	GET  /cases/{id}
//	POST /cases/{id}/review   {"status": "approved|rejected", "analyst": "...", "notes": "..."}
func Handler(svc *Service, log *slog.Logger) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("GET /cases", func(w http.ResponseWriter, r *http.Request) {
		size, err := strconv.Atoi(r.URL.Query().Get("size"))
		if err != nil || size < 1 || size > 500 {
			size = 50
		}
		list, err := svc.Store.List(r.Context(), r.URL.Query().Get("review_status"), size)
		if err != nil {
			log.Error("list cases", "error", err)
			writeError(w, http.StatusBadGateway, "could not list cases")
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"cases": list, "count": len(list)})
	})
	mux.HandleFunc("GET /cases/{id}", func(w http.ResponseWriter, r *http.Request) {
		c, err := svc.Store.Get(r.Context(), r.PathValue("id"))
		switch {
		case errors.Is(err, ErrNotFound):
			writeError(w, http.StatusNotFound, "case not found")
		case err != nil:
			log.Error("get case", "error", err)
			writeError(w, http.StatusBadGateway, "could not read case")
		default:
			writeJSON(w, http.StatusOK, c)
		}
	})
	mux.HandleFunc("POST /cases/{id}/review", func(w http.ResponseWriter, r *http.Request) {
		var rv Review
		if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 64<<10)).Decode(&rv); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON body")
			return
		}
		c, err := svc.Review(r.Context(), r.PathValue("id"), rv)
		switch {
		case errors.Is(err, ErrInvalidReview), errors.Is(err, ErrInvalidAnalyst):
			writeError(w, http.StatusBadRequest, err.Error())
		case errors.Is(err, ErrNotFound):
			writeError(w, http.StatusNotFound, "case not found")
		case err != nil:
			log.Error("review case", "error", err)
			writeError(w, http.StatusBadGateway, "could not update case")
		default:
			log.Info("case reviewed", "case_id", logSafe(c.ID), "status", c.ReviewStatus,
				"analyst", logSafe(c.ReviewedBy))
			writeJSON(w, http.StatusOK, c)
		}
	})
	return mux
}

// logSafe drops line breaks from request-derived values before they are logged. The JSON log
// handler escapes them anyway; this keeps the log safe with any handler.
func logSafe(s string) string {
	return strings.ReplaceAll(strings.ReplaceAll(s, "\n", ""), "\r", "")
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
