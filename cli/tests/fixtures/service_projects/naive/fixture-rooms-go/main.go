// Rooms: desk passes counted in the data folder, and the room vendor's rooms.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
)

var (
	day       = regexp.MustCompile(`^[0-9]{4}-[0-9]{2}-[0-9]{2}$`)
	stockFile = filepath.Join(os.Getenv("CSTUDY_DATA_DIR"), "stock.json")
	vendorURL = os.Getenv("ROOM_VENDOR_URL") + "/v1/rooms"
	vendor    = &http.Client{}
	degraded  = map[string]any{"rooms": []any{}, "degraded": true}
)

type stock struct {
	Available int `json:"available"`
}

func main() {
	address := ":" + os.Getenv("PORT")
	log.Printf("listening on %s", address)
	log.Fatal(http.ListenAndServe(address, routes()))
}

func routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, _ *http.Request) {
		answer(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("GET /desks", desks)
	mux.HandleFunc("POST /desks/book", book)
	mux.HandleFunc("GET /rooms", rooms)
	mux.HandleFunc("/", func(w http.ResponseWriter, _ *http.Request) {
		answer(w, http.StatusNotFound, map[string]string{"error": "not found"})
	})
	return mux
}

func desks(w http.ResponseWriter, r *http.Request) {
	date := r.URL.Query().Get("date")
	if !day.MatchString(date) {
		answer(w, http.StatusBadRequest, map[string]string{"error": "date is required"})
		return
	}
	left, err := available()
	if err != nil {
		answer(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}
	answer(w, http.StatusOK, map[string]any{"date": date, "available": left.Available})
}

func book(w http.ResponseWriter, _ *http.Request) {
	left, err := available()
	if err == nil {
		left.Available--
		err = keep(left)
	}
	if err != nil {
		answer(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}
	answer(w, http.StatusCreated, left)
}

func available() (stock, error) {
	var found stock
	content, err := os.ReadFile(stockFile)
	if err == nil {
		err = json.Unmarshal(content, &found)
	}
	return found, err
}

func keep(left stock) error {
	content, err := json.Marshal(left)
	if err != nil {
		return err
	}
	return os.WriteFile(stockFile, content, 0o644)
}

func rooms(w http.ResponseWriter, r *http.Request) {
	found, err := vendorRooms(r.Context())
	if err != nil {
		log.Printf("room-vendor: %v", err)
		answer(w, http.StatusOK, degraded)
		return
	}
	answer(w, http.StatusOK, map[string]any{"rooms": found, "degraded": false})
}

// vendorRooms asks the vendor once, with no limit on how long it takes.
func vendorRooms(ctx context.Context) ([]json.RawMessage, error) {
	response, err := vendorCall(ctx)
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("answered %d", response.StatusCode)
	}
	var body struct {
		Rooms []json.RawMessage `json:"rooms"`
	}
	if err := json.NewDecoder(response.Body).Decode(&body); err != nil {
		return nil, err
	}
	if body.Rooms == nil {
		return nil, errors.New("sent no rooms")
	}
	return body.Rooms, nil
}

func vendorCall(ctx context.Context) (*http.Response, error) {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, vendorURL, nil)
	if err != nil {
		return nil, err
	}
	return vendor.Do(request)
}

func answer(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(body); err != nil {
		log.Printf("answering: %v", err)
	}
}
