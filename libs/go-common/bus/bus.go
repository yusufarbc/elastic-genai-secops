// Package bus is the message bus abstraction shared by the Go services (ADR-017).
package bus

import (
	"context"
	"fmt"

	"esm/libs/go-common/envx"
)

// Handler processes one message. Returning an error asks the bus to redeliver it later.
type Handler func(ctx context.Context, data []byte) error

// Bus publishes JSON messages and runs durable subscriptions.
type Bus interface {
	// Publish sends v as JSON. msgID is used for duplicate detection; pass "" to skip it.
	Publish(ctx context.Context, subject, msgID string, v any) error
	// Subscribe consumes subject with a durable consumer and blocks until ctx is cancelled.
	Subscribe(ctx context.Context, subject, durable string, h Handler) error
	Close() error
}

// FromEnv returns the backend selected by BUS_BACKEND (default "nats").
func FromEnv(ctx context.Context) (Bus, error) {
	switch backend := envx.String("BUS_BACKEND", "nats"); backend {
	case "nats":
		return NewNATS(ctx, envx.String("NATS_URL", "nats://nats:4222"))
	default:
		// The GCP Pub/Sub adapter is planned (ADR-017); see ROADMAP.md.
		return nil, fmt.Errorf("unsupported BUS_BACKEND %q (supported: nats)", backend)
	}
}
