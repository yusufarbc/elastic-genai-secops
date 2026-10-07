package cases

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"
)

// tokenPattern matches masking-service tokens (prefix + 6 hex chars, see services/masking-service).
var tokenPattern = regexp.MustCompile(`\b(?:user|host|ip|email|tok)_[0-9a-f]{6}\b`)

// Unmasker resolves tokens for one incident.
type Unmasker interface {
	ReverseMap(ctx context.Context, incidentID string) (map[string]string, error)
}

// MaskingClient fetches reverse-maps from masking-service, the only holder of plaintext mappings.
// case-service uses the map transiently while building a case and never persists it.
type MaskingClient struct {
	BaseURL string
	HTTP    *http.Client
}

// NewMaskingClient returns a client for masking-service at baseURL.
func NewMaskingClient(baseURL string) *MaskingClient {
	return &MaskingClient{BaseURL: strings.TrimRight(baseURL, "/"), HTTP: &http.Client{Timeout: 15 * time.Second}}
}

// ReverseMap implements Unmasker.
func (c *MaskingClient) ReverseMap(ctx context.Context, incidentID string) (map[string]string, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.BaseURL+"/map/"+url.PathEscape(incidentID), nil)
	if err != nil {
		return nil, err
	}
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("masking-service /map: HTTP %d", resp.StatusCode)
	}
	var body struct {
		TokenToPlain map[string]string `json:"token_to_plain"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		return nil, err
	}
	return body.TokenToPlain, nil
}

// unmaskText replaces every known token in s with its plaintext; unknown tokens are left as-is.
func unmaskText(s string, m map[string]string) string {
	return tokenPattern.ReplaceAllStringFunc(s, func(tok string) string {
		if plain, ok := m[tok]; ok {
			return plain
		}
		return tok
	})
}

func unmaskAll(ss []string, m map[string]string) []string {
	out := make([]string, len(ss))
	for i, s := range ss {
		out[i] = unmaskText(s, m)
	}
	return out
}
