package main

import (
	"net/http"
	"os"
	"reflect"
	"strings"
	"testing"
)

// app serves the API in the test's own process, over the seeded desks and the stack's vendors.
func app(t *testing.T) string {
	t.Helper()
	desks, err := loadDesks("data/desks.json")
	if err != nil {
		t.Fatal(err)
	}
	vendors := vendorsAt(os.Getenv("ROOM_VENDOR_URL"), os.Getenv("ANNEX_VENDOR_URL"))
	return serve(t, newServer(desks, vendors))
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

func TestAWrongRequestIsRefusedOnBothEndpoints(t *testing.T) {
	refusals := []struct {
		query  string
		status int
		reason string
	}{
		{"", http.StatusBadRequest, "date is required"},
		{"?date=", http.StatusBadRequest, "date is required"},
		{"?date=2027-02-30", http.StatusBadRequest, "date must be a real day, as YYYY-MM-DD"},
		{"?date=2027-04-01", http.StatusNotFound, "no desks on sale for that date"},
	}
	base := app(t)
	for _, path := range []string{"/desks", "/availability"} {
		for _, refused := range refusals {
			status, body := get(t, base, path+refused.query)

			want := fromJSON(t, `{"error": "`+refused.reason+`"}`)
			if status != refused.status || !reflect.DeepEqual(body, want) {
				t.Errorf("%s%s answered %d %v, want %d %v",
					path, refused.query, status, body, refused.status, want)
			}
		}
	}
}

func TestAnotherMethodOnAKnownPathIsNotAllowed(t *testing.T) {
	response, err := http.Post(app(t)+"/desks?date=2027-03-01", "application/json", strings.NewReader("{}"))
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()

	if response.StatusCode != http.StatusMethodNotAllowed {
		t.Errorf("POST /desks answered %d, want %d", response.StatusCode, http.StatusMethodNotAllowed)
	}
}
