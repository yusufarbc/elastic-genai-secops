package pubsub

import (
	"context"

	"esm/alert-gateway/internal/incident"
)

// AlertSubscriber receives normalized alerts from the esm.alerts topic.
type AlertSubscriber interface {
	Subscribe(ctx context.Context, handler func(ctx context.Context, a *incident.Alert) error) error
	Close() error
}

// IncidentPublisher sends formed incidents to the esm.incidents topic.
type IncidentPublisher interface {
	Publish(ctx context.Context, inc *incident.Incident) error
	Close() error
}
