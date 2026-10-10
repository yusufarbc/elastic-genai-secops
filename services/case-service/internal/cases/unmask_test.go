package cases

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestMaskingClientDeleteMap(t *testing.T) {
	var gotMethod, gotPath string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotMethod, gotPath = r.Method, r.URL.EscapedPath()
		w.WriteHeader(http.StatusNoContent)
	}))
	defer srv.Close()

	if err := NewMaskingClient(srv.URL+"/").DeleteMap(context.Background(), "inc/1"); err != nil {
		t.Fatal(err)
	}
	if gotMethod != http.MethodDelete || gotPath != "/map/inc%2F1" {
		t.Errorf("request = %s %s", gotMethod, gotPath)
	}
}

func TestMaskingClientDeleteMapError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer srv.Close()

	if err := NewMaskingClient(srv.URL).DeleteMap(context.Background(), "inc-1"); err == nil {
		t.Fatal("expected an error for HTTP 500")
	}
}
