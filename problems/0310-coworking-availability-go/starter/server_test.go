package main

import (
	"net/http"
	"reflect"
	"testing"
)

// app serves the API in the test's own process, over the seeded desks.
func app(t *testing.T) string {
	t.Helper()
	desks, err := loadDesks("data/desks.json")
	if err != nil {
		t.Fatal(err)
	}
	return serve(t, newServer(desks))
}

func TestTheServiceAnswersItsHealthPath(t *testing.T) {
	status, _ := get(t, app(t), "/health")

	if status != http.StatusOK {
		t.Errorf("GET /health answered %d, want %d", status, http.StatusOK)
	}
}

func TestADayOnSaleAnswersItsCount(t *testing.T) {
	status, body := get(t, app(t), "/desks?date=2027-03-01")

	want := fromJSON(t, `{"date": "2027-03-01", "available": 12}`)
	if status != http.StatusOK || !reflect.DeepEqual(body, want) {
		t.Errorf("answered %d %v, want 200 %v", status, body, want)
	}
}

func TestNoDateIsABadRequest(t *testing.T) {
	status, body := get(t, app(t), "/desks")

	want := fromJSON(t, `{"error": "date is required"}`)
	if status != http.StatusBadRequest || !reflect.DeepEqual(body, want) {
		t.Errorf("answered %d %v, want 400 %v", status, body, want)
	}
}
