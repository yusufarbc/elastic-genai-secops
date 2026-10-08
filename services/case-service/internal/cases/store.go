package cases

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"strings"

	"esm/libs/go-common/es"
)

// Index holds one document per case (document ID = incident ID).
const Index = "esm-cases"

// ErrExists is returned by Create when the case already exists.
var ErrExists = errors.New("case already exists")

// ErrNotFound is returned when a case does not exist.
var ErrNotFound = errors.New("case not found")

// Store persists cases.
type Store interface {
	Create(ctx context.Context, c *Case) error
	Put(ctx context.Context, c *Case) error
	Get(ctx context.Context, id string) (*Case, error)
	List(ctx context.Context, reviewStatus string, size int) ([]*Case, error)
}

// ESStore stores cases in Elasticsearch.
type ESStore struct{ ES *es.Client }

var indexMapping = map[string]any{
	"mappings": map[string]any{
		"dynamic": "false",
		"properties": map[string]any{
			"id":               map[string]any{"type": "keyword"},
			"incident_id":      map[string]any{"type": "keyword"},
			"created_at":       map[string]any{"type": "date"},
			"updated_at":       map[string]any{"type": "date"},
			"triage_status":    map[string]any{"type": "keyword"},
			"review_status":    map[string]any{"type": "keyword"},
			"reviewed_by":      map[string]any{"type": "keyword"},
			"severity":         map[string]any{"type": "keyword"},
			"risk_score":       map[string]any{"type": "integer"},
			"alert_count":      map[string]any{"type": "integer"},
			"summary":          map[string]any{"type": "text"},
			"mitre_techniques": map[string]any{"type": "keyword"},
			"affected_hosts":   map[string]any{"type": "keyword"},
			"affected_users":   map[string]any{"type": "keyword"},
			"source_ips":       map[string]any{"type": "keyword"},
			"model_id":         map[string]any{"type": "keyword"},
		},
	},
}

// EnsureIndex creates the index with its mapping if it does not exist.
func (s *ESStore) EnsureIndex(ctx context.Context) error {
	err := s.ES.Do(ctx, http.MethodHead, "/"+Index, nil, nil)
	if err == nil {
		return nil
	}
	if !errors.Is(err, es.ErrNotFound) {
		return err
	}
	err = s.ES.Do(ctx, http.MethodPut, "/"+Index, indexMapping, nil)
	if err != nil && strings.Contains(err.Error(), "resource_already_exists_exception") {
		return nil
	}
	return err
}

// Create implements Store (op_type=create, so redeliveries do not overwrite reviews).
func (s *ESStore) Create(ctx context.Context, c *Case) error {
	err := s.ES.Do(ctx, http.MethodPut, "/"+Index+"/_create/"+url.PathEscape(c.ID)+"?refresh=wait_for", c, nil)
	if err != nil && strings.Contains(err.Error(), "HTTP 409") {
		return ErrExists
	}
	return err
}

// Put implements Store.
func (s *ESStore) Put(ctx context.Context, c *Case) error {
	return s.ES.Do(ctx, http.MethodPut, "/"+Index+"/_doc/"+url.PathEscape(c.ID)+"?refresh=wait_for", c, nil)
}

// Get implements Store.
func (s *ESStore) Get(ctx context.Context, id string) (*Case, error) {
	var doc struct {
		Source Case `json:"_source"`
	}
	err := s.ES.Do(ctx, http.MethodGet, "/"+Index+"/_doc/"+url.PathEscape(id), nil, &doc)
	if errors.Is(err, es.ErrNotFound) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &doc.Source, nil
}

// List implements Store, newest first. An empty reviewStatus lists all cases.
func (s *ESStore) List(ctx context.Context, reviewStatus string, size int) ([]*Case, error) {
	query := map[string]any{"match_all": map[string]any{}}
	if reviewStatus != "" {
		query = map[string]any{"term": map[string]any{"review_status": reviewStatus}}
	}
	var res struct {
		Hits struct {
			Hits []struct {
				Source Case `json:"_source"`
			} `json:"hits"`
		} `json:"hits"`
	}
	body := map[string]any{"size": size, "query": query, "sort": []any{map[string]any{"created_at": "desc"}}}
	if err := s.ES.Do(ctx, http.MethodPost, "/"+Index+"/_search", body, &res); err != nil {
		return nil, fmt.Errorf("list cases: %w", err)
	}
	out := make([]*Case, 0, len(res.Hits.Hits))
	for i := range res.Hits.Hits {
		out = append(out, &res.Hits.Hits[i].Source)
	}
	return out, nil
}
