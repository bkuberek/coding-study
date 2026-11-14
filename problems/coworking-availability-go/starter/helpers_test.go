package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"
)

const askLimit = 30 * time.Second

// serve runs handler on a port of its own until the test ends, and gives its base URL.
func serve(t *testing.T, handler http.Handler) string {
	t.Helper()
	server := httptest.NewServer(handler)
	t.Cleanup(server.Close)
	return server.URL
}

// get is the status and the JSON body that base answers to GET path, as cstudy's cases ask your
// app, errors included.
func get(t *testing.T, base, path string) (int, any) {
	t.Helper()
	client := http.Client{Timeout: askLimit}
	response, err := client.Get(base + path)
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	var body any
	if err := json.NewDecoder(response.Body).Decode(&body); err != nil {
		t.Fatalf("GET %s answered no JSON: %v", path, err)
	}
	return response.StatusCode, body
}

// fromJSON is text decoded as get decodes a body, to compare the two.
func fromJSON(t *testing.T, text string) any {
	t.Helper()
	var value any
	if err := json.Unmarshal([]byte(text), &value); err != nil {
		t.Fatal(err)
	}
	return value
}

// setScenario makes vendor behave as scenario says, or as usual for "", through the mock servers'
// control interface, whose address and token cstudy test gives your tests. Only the scenarios in a
// vendor's API.md are there.
func setScenario(t *testing.T, vendor, scenario string) {
	t.Helper()
	var chosen any
	if scenario != "" {
		chosen = scenario
	}
	body, err := json.Marshal(map[string]any{"scenario": chosen})
	if err != nil {
		t.Fatal(err)
	}
	control(t, http.MethodPut, "mocks/"+vendor+"/scenario", body)
}

// resetVendors puts every vendor back to no scenario.
func resetVendors(t *testing.T) {
	t.Helper()
	control(t, http.MethodPost, "reset", nil)
}

func control(t *testing.T, method, path string, body []byte) {
	t.Helper()
	url := os.Getenv("CSTUDY_MOCK_CONTROL_URL") + "/" + path
	request, err := http.NewRequest(method, url, bytes.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	request.Header.Set("Authorization", "Bearer "+os.Getenv("CSTUDY_MOCK_CONTROL_TOKEN"))
	request.Header.Set("Content-Type", "application/json")
	client := http.Client{Timeout: askLimit}
	response, err := client.Do(request)
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	if response.StatusCode >= http.StatusMultipleChoices {
		t.Fatalf("the mock control answered %d to %s %s", response.StatusCode, method, path)
	}
}
