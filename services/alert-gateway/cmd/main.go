// alert-gateway correlates alerts from esm.alerts into incidents on esm.incidents.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"esm/services/alert-gateway/internal/incident"

	"esm/libs/go-common/bus"
	"esm/libs/go-common/contracts"
	"esm/libs/go-common/envx"
)

func main() {
	log := envx.Logger("alert-gateway")
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	b, err := bus.FromEnv(ctx)
	if err != nil {
		log.Error("bus connect", "error", err)
		os.Exit(1)
	}
	defer b.Close()

	threshold := envx.Int("CORRELATION_THRESHOLD", 5)
	window := envx.Duration("CORRELATION_WINDOW", 10*time.Minute)
	correlator := incident.NewCorrelator(threshold, window)

	publish := func(ctx context.Context, inc *contracts.Incident) error {
		if err := b.Publish(ctx, contracts.SubjectIncidents, inc.ID, inc); err != nil {
			return err
		}
		log.Info("incident published", "incident_id", inc.ID, "alerts", inc.AlertCount, "risk", inc.RiskScore)
		return nil
	}

	go flushLoop(ctx, log, correlator, publish)

	log.Info("alert-gateway started", "threshold", threshold, "window", window.String())
	err = b.Subscribe(ctx, contracts.SubjectAlerts, "alert-gateway", func(ctx context.Context, data []byte) error {
		var a contracts.Alert
		if err := json.Unmarshal(data, &a); err != nil {
			log.Error("invalid alert message, dropping", "error", err)
			return nil
		}
		if inc := correlator.Ingest(&a); inc != nil {
			if err := publish(ctx, inc); err != nil {
				return fmt.Errorf("publish incident: %w", err)
			}
		}
		return nil
	})
	if err != nil && !errors.Is(err, context.Canceled) {
		log.Error("alert-gateway stopped with error", "error", err)
		os.Exit(1)
	}
	log.Info("alert-gateway stopped")
}

// flushLoop emits incidents whose correlation window expired before reaching the threshold.
// Note: open buckets live in memory; alerts of an unfinished window are lost on restart
// (they are acknowledged on ingest). Persisting buckets is tracked in ROADMAP.md.
func flushLoop(ctx context.Context, log *slog.Logger, c *incident.Correlator, publish func(context.Context, *contracts.Incident) error) {
	t := time.NewTicker(15 * time.Second)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			for _, inc := range c.Flush() {
				if err := publish(ctx, inc); err != nil {
					log.Error("incident publish failed", "incident_id", inc.ID, "error", err)
				}
			}
		}
	}
}
