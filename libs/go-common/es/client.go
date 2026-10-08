// Package es is a minimal Elasticsearch REST client (net/http only, no SDK).
package es

import (
	"bytes"
	"context"
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"esm/libs/go-common/envx"
)

// ErrNotFound is returned for HTTP 404 responses.
var ErrNotFound = errors.New("elasticsearch: not found")

// Client talks to one Elasticsearch endpoint with basic auth.
type Client struct {
	baseURL  string
	user     string
	password string
	http     *http.Client
}

// FromEnv builds a client from ELASTIC_URL, ELASTIC_USER, ELASTIC_PASSWORD and ELASTIC_CA_CERTS.
func FromEnv() (*Client, error) {
	tlsCfg := &tls.Config{MinVersion: tls.VersionTLS12}
	if caPath := os.Getenv("ELASTIC_CA_CERTS"); caPath != "" {
		pem, err := os.ReadFile(caPath)
		if err != nil {
			return nil, fmt.Errorf("read ELASTIC_CA_CERTS: %w", err)
		}
		pool := x509.NewCertPool()
		if !pool.AppendCertsFromPEM(pem) {
			return nil, fmt.Errorf("no certificates found in %s", caPath)
		}
		tlsCfg.RootCAs = pool
	}
	return &Client{
		baseURL:  strings.TrimRight(envx.String("ELASTIC_URL", "https://localhost:9200"), "/"),
		user:     envx.String("ELASTIC_USER", "elastic"),
		password: os.Getenv("ELASTIC_PASSWORD"),
		http: &http.Client{
			Timeout:   30 * time.Second,
			Transport: &http.Transport{TLSClientConfig: tlsCfg},
		},
	}, nil
}

// Do sends a request with an optional JSON body and decodes a JSON response into out (if non-nil).
func (c *Client) Do(ctx context.Context, method, path string, body, out any) error {
	var reader io.Reader
	if body != nil {
		buf, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("encode request: %w", err)
		}
		reader = bytes.NewReader(buf)
	}
	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, reader)
	if err != nil {
		return err
	}
	req.SetBasicAuth(c.user, c.password)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}
	if resp.StatusCode == http.StatusNotFound {
		return ErrNotFound
	}
	if resp.StatusCode >= 300 {
		return fmt.Errorf("elasticsearch %s %s: HTTP %d: %s", method, path, resp.StatusCode, truncate(data, 500))
	}
	if out != nil && len(data) > 0 {
		if err := json.Unmarshal(data, out); err != nil {
			return fmt.Errorf("decode response: %w", err)
		}
	}
	return nil
}

func truncate(b []byte, n int) string {
	if len(b) > n {
		return string(b[:n]) + "..."
	}
	return string(b)
}
