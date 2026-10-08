// Package internal implements detection-service: it reads new Kibana Security alerts from
// Elasticsearch and publishes them, normalized, to esm.alerts.
package internal

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"time"

	"esm/libs/go-common/bus"
	"esm/libs/go-common/contracts"
	"esm/libs/go-common/es"
)

const (
	alertsIndex  = ".alerts-security.alerts-*"
	stateIndex   = "esm-state"
	checkpointID = "detection-service"
	pageSize     = 200
)

// Checkpoint is the search_after position of the last published alert, stored in esm-state.
type Checkpoint struct {
	TimestampMillis int64  `json:"timestamp_millis"`
	AlertUUID       string `json:"alert_uuid"`
}

// Service polls Elasticsearch and publishes alerts.
type Service struct {
	es        *es.Client
	bus       bus.Bus
	log       *slog.Logger
	pollEvery time.Duration
	lookback  time.Duration
}

// New returns a Service.
func New(esClient *es.Client, b bus.Bus, log *slog.Logger, pollEvery, lookback time.Duration) *Service {
	return &Service{es: esClient, bus: b, log: log, pollEvery: pollEvery, lookback: lookback}
}

// Run polls until ctx is cancelled.
func (s *Service) Run(ctx context.Context) error {
	cp := s.loadCheckpoint(ctx)
	s.log.Info("starting from checkpoint", "timestamp", time.UnixMilli(cp.TimestampMillis).UTC(), "alert_uuid", cp.AlertUUID)

	ticker := time.NewTicker(s.pollEvery)
	defer ticker.Stop()
	for {
		next, err := s.poll(ctx, cp)
		if err != nil {
			s.log.Warn("poll failed", "error", err)
		} else if next != cp {
			cp = next
			if err := s.es.Do(ctx, http.MethodPut, "/"+stateIndex+"/_doc/"+checkpointID, cp, nil); err != nil {
				s.log.Warn("checkpoint save failed", "error", err)
			}
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
		}
	}
}

type searchResponse struct {
	Hits struct {
		Hits []struct {
			ID     string         `json:"_id"`
			Source map[string]any `json:"_source"`
			Sort   []any          `json:"sort"`
		} `json:"hits"`
	} `json:"hits"`
}

// poll publishes every open alert after cp and returns the new checkpoint.
func (s *Service) poll(ctx context.Context, cp Checkpoint) (Checkpoint, error) {
	for {
		query := map[string]any{
			"size": pageSize,
			"sort": []any{
				map[string]any{"@timestamp": "asc"},
				map[string]any{"kibana.alert.uuid": "asc"},
			},
			"search_after": []any{cp.TimestampMillis, cp.AlertUUID},
			"query": map[string]any{"bool": map[string]any{"filter": []any{
				map[string]any{"term": map[string]any{"kibana.alert.workflow_status": "open"}},
			}}},
		}
		var res searchResponse
		err := s.es.Do(ctx, http.MethodPost, "/"+alertsIndex+"/_search?allow_no_indices=true", query, &res)
		if errors.Is(err, es.ErrNotFound) {
			return cp, nil // no alerts index yet
		}
		if err != nil {
			return cp, err
		}
		for _, hit := range res.Hits.Hits {
			alert := Normalize(hit.ID, hit.Source)
			if err := s.bus.Publish(ctx, contracts.SubjectAlerts, alert.ID, alert); err != nil {
				return cp, err // retry from the last published alert on the next poll
			}
			s.log.Info("alert published", "alert_id", alert.ID, "rule_id", alert.RuleID, "host", alert.HostName)
			if len(hit.Sort) == 2 {
				ms, _ := hit.Sort[0].(float64) // date sort values are epoch milliseconds
				uuid, _ := hit.Sort[1].(string)
				cp = Checkpoint{TimestampMillis: int64(ms), AlertUUID: uuid}
			}
		}
		if len(res.Hits.Hits) < pageSize {
			return cp, nil
		}
	}
}

func (s *Service) loadCheckpoint(ctx context.Context) Checkpoint {
	var doc struct {
		Source Checkpoint `json:"_source"`
	}
	err := s.es.Do(ctx, http.MethodGet, "/"+stateIndex+"/_doc/"+checkpointID, nil, &doc)
	if err == nil && doc.Source.TimestampMillis > 0 {
		return doc.Source
	}
	if err != nil && !errors.Is(err, es.ErrNotFound) {
		s.log.Warn("checkpoint read failed, starting from lookback", "error", err)
	}
	return Checkpoint{TimestampMillis: time.Now().Add(-s.lookback).UnixMilli()}
}
