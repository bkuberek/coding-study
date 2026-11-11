// The coworking space's API: what can be booked on a day.
package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	desks, err := loadDesks("data/desks.json")
	if err != nil {
		log.Fatal(err)
	}
	address := ":" + os.Getenv("PORT")
	log.Printf("listening on %s", address)
	log.Fatal(http.ListenAndServe(address, newServer(desks)))
}
