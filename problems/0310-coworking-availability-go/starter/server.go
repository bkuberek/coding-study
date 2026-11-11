package main

import (
	"encoding/json"
	"log"
	"net/http"
)

// newServer answers every request of the API.
func newServer(desks deskInventory) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) {
		answer(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("/desks", func(w http.ResponseWriter, r *http.Request) {
		date := r.URL.Query().Get("date")
		available, _ := desks.availableOn(date)
		answer(w, http.StatusOK, deskCount{Date: date, Available: available})
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, _ *http.Request) {
		answer(w, http.StatusNotFound, map[string]string{"error": "not found"})
	})
	return mux
}

type deskCount struct {
	Date      string `json:"date"`
	Available int    `json:"available"`
}

// answer writes body as JSON, with status.
func answer(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(body); err != nil {
		log.Printf("answering: %v", err)
	}
}
