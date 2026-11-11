package main

import (
	"encoding/json"
	"log"
	"net/http"
	"time"

	"coworking/internal/rooms"
)

// reply is a status and a body for encoding/json to write.
type reply struct {
	status int
	body   any
}

var (
	notFound         = refusal(http.StatusNotFound, "not found")
	methodNotAllowed = refusal(http.StatusMethodNotAllowed, "method not allowed")
	noDate           = refusal(http.StatusBadRequest, "date is required")
	notADay          = refusal(http.StatusBadRequest, "date must be a real day, as YYYY-MM-DD")
	notOnSale        = refusal(http.StatusNotFound, "no desks on sale for that date")
)

func refusal(status int, reason string) *reply {
	return &reply{status, map[string]string{"error": reason}}
}

type deskCount struct {
	Date      string `json:"date"`
	Available int    `json:"available"`
}

type deskLeft struct {
	Available int `json:"available"`
}

type dayAvailability struct {
	Date  string           `json:"date"`
	Desks deskLeft         `json:"desks"`
	Rooms roomAvailability `json:"rooms"`
}

// api answers from the desks the space holds itself and the rooms its vendors sell.
type api struct {
	desks   deskInventory
	vendors []rooms.Source
}

// newServer answers every request of the API. The routes are a map, so a path the API has
// answers 405 to another method in one place, and a path it lacks 404, both in JSON.
func newServer(desks deskInventory, vendors []rooms.Source) http.Handler {
	service := api{desks, vendors}
	routes := map[string]func(*http.Request) reply{
		"/health":       func(*http.Request) reply { return reply{http.StatusOK, map[string]string{"status": "ok"}} },
		"/desks":        service.desksOn,
		"/availability": service.availabilityOn,
	}
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		route, known := routes[r.URL.Path]
		switch {
		case !known:
			write(w, *notFound)
		case r.Method != http.MethodGet:
			write(w, *methodNotAllowed)
		default:
			write(w, route(r))
		}
	})
}

// dayOnSale is the day the request's date names, or the reply that refuses it: before any vendor
// hears of it.
func (a api) dayOnSale(r *http.Request) (string, time.Time, *reply) {
	date := r.URL.Query().Get("date")
	if date == "" {
		return date, time.Time{}, noDate
	}
	day, exists := parseDay(date)
	if !exists {
		return date, day, notADay
	}
	if _, onSale := a.desks.availableOn(date); !onSale {
		return date, day, notOnSale
	}
	return date, day, nil
}

func (a api) desksOn(r *http.Request) reply {
	date, _, refused := a.dayOnSale(r)
	if refused != nil {
		return *refused
	}
	left, _ := a.desks.availableOn(date)
	return reply{http.StatusOK, deskCount{date, left}}
}

func (a api) availabilityOn(r *http.Request) reply {
	date, day, refused := a.dayOnSale(r)
	if refused != nil {
		return *refused
	}
	left, _ := a.desks.availableOn(date)
	found := askEveryVendor(r.Context(), day, a.vendors)
	return reply{http.StatusOK, dayAvailability{date, deskLeft{left}, found}}
}

func write(w http.ResponseWriter, answer reply) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(answer.status)
	if err := json.NewEncoder(w).Encode(answer.body); err != nil {
		log.Printf("answering: %v", err)
	}
}
