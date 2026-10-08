// detection-service reads Kibana Security alerts and publishes them to esm.alerts.
package main

import (
	"context"
	"errors"
	"os"
	"os/signal"
	"syscall"
	"time"

	internal "esm/services/detection-service/internal"

	"esm/libs/go-common/bus"
	"esm/libs/go-common/envx"
	"esm/libs/go-common/es"
)

func main() {
	log := envx.Logger("detection-service")
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	esClient, err := es.FromEnv()
	if err != nil {
		log.Error("elasticsearch config", "error", err)
		os.Exit(1)
	}
	b, err := bus.FromEnv(ctx)
	if err != nil {
		log.Error("bus connect", "error", err)
		os.Exit(1)
	}
	defer b.Close()

	svc := internal.New(esClient, b, log,
		envx.Duration("DETECTION_POLL_INTERVAL", 30*time.Second),
		envx.Duration("DETECTION_LOOKBACK", time.Hour),
	)
	log.Info("detection-service started")
	if err := svc.Run(ctx); err != nil && !errors.Is(err, context.Canceled) {
		log.Error("detection-service stopped with error", "error", err)
		os.Exit(1)
	}
	log.Info("detection-service stopped")
}
