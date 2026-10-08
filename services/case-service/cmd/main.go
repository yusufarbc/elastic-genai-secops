// case-service turns triage results into analyst cases and serves the case API.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"esm/services/case-service/internal/cases"

	"esm/libs/go-common/bus"
	"esm/libs/go-common/contracts"
	"esm/libs/go-common/envx"
	"esm/libs/go-common/es"
)

func main() {
	log := envx.Logger("case-service")
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	esClient, err := es.FromEnv()
	if err != nil {
		log.Error("elasticsearch config", "error", err)
		os.Exit(1)
	}
	store := &cases.ESStore{ES: esClient}
	for {
		if err = store.EnsureIndex(ctx); err == nil {
			break
		}
		log.Warn("waiting for Elasticsearch", "error", err)
		select {
		case <-ctx.Done():
			return
		case <-time.After(5 * time.Second):
		}
	}

	svc := &cases.Service{
		Store:    store,
		Unmasker: cases.NewMaskingClient(envx.String("MASKING_SERVICE_URL", "http://masking-service:8001")),
		Now:      func() time.Time { return time.Now().UTC() },
		Log:      log,
	}

	srv := &http.Server{
		Addr:              envx.String("LISTEN_ADDR", ":8002"),
		Handler:           cases.Handler(svc, log),
		ReadHeaderTimeout: 10 * time.Second,
	}
	go func() {
		log.Info("case API listening", "addr", srv.Addr)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Error("case API failed", "error", err)
			stop()
		}
	}()

	b, err := bus.FromEnv(ctx)
	if err != nil {
		log.Error("bus connect", "error", err)
		os.Exit(1)
	}
	defer b.Close()
	svc.Events = b // case events for outbound-service (notifications, tickets)

	err = b.Subscribe(ctx, contracts.SubjectTriageResults, "case-service", func(ctx context.Context, data []byte) error {
		var r contracts.TriageResult
		if err := json.Unmarshal(data, &r); err != nil || r.IncidentID == "" {
			log.Error("invalid triage result, dropping", "error", err)
			return nil
		}
		c, err := svc.FromTriageResult(ctx, &r)
		if err != nil {
			return fmt.Errorf("create case %s: %w", r.IncidentID, err)
		}
		log.Info("case created", "case_id", c.ID, "triage_status", c.TriageStatus, "severity", c.Severity)
		return nil
	})
	if err != nil && !errors.Is(err, context.Canceled) {
		log.Error("subscription stopped", "error", err)
	}

	shutdown, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = srv.Shutdown(shutdown)
	log.Info("case-service stopped")
}
