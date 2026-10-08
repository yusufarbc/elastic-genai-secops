// Package envx reads typed configuration from environment variables.
package envx

import (
	"log/slog"
	"os"
	"strconv"
	"time"
)

// String returns the variable or def when unset or empty.
func String(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

// Int returns the variable parsed as int, or def when unset or invalid.
func Int(key string, def int) int {
	v := os.Getenv(key)
	if v == "" {
		return def
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		slog.Warn("invalid integer in environment, using default", "key", key, "value", v, "default", def)
		return def
	}
	return n
}

// Duration returns the variable parsed with time.ParseDuration, or def when unset or invalid.
func Duration(key string, def time.Duration) time.Duration {
	v := os.Getenv(key)
	if v == "" {
		return def
	}
	d, err := time.ParseDuration(v)
	if err != nil {
		slog.Warn("invalid duration in environment, using default", "key", key, "value", v, "default", def)
		return def
	}
	return d
}

// Logger returns a JSON slog logger tagged with the service name and installs it as default.
func Logger(service string) *slog.Logger {
	level := slog.LevelInfo
	if os.Getenv("LOG_LEVEL") == "debug" {
		level = slog.LevelDebug
	}
	log := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: level})).With("service", service)
	slog.SetDefault(log)
	return log
}
