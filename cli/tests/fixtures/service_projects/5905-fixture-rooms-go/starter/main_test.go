package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/google/go-cmp/cmp"
)

func TestTheServiceAnswersItsHealthPath(t *testing.T) {
	server := httptest.NewServer(routes())
	defer server.Close()

	response, err := http.Get(server.URL + "/health")
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	var body map[string]string
	if err := json.NewDecoder(response.Body).Decode(&body); err != nil {
		t.Fatal(err)
	}

	if diff := cmp.Diff(map[string]string{"status": "ok"}, body); diff != "" {
		t.Errorf("GET /health (-want +got):\n%s", diff)
	}
}
