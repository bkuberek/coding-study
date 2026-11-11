// Rooms: desk passes and meeting rooms, which you build level by level.
package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
)

func main() {
	address := ":" + os.Getenv("PORT")
	log.Printf("listening on %s", address)
	log.Fatal(http.ListenAndServe(address, routes()))
}

func routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) {
		answer(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, _ *http.Request) {
		answer(w, http.StatusNotFound, map[string]string{"error": "not found"})
	})
	return mux
}

func answer(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(body); err != nil {
		log.Printf("answering: %v", err)
	}
}
