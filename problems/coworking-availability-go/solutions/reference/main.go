// The coworking space's API: what can be booked on a day.
package main

import (
	"log"
	"net/http"
	"os"

	"coworking/internal/rooms"
)

func main() {
	desks, err := loadDesks("data/desks.json")
	if err != nil {
		log.Fatal(err)
	}
	vendors := vendorsAt(os.Getenv("ROOM_VENDOR_URL"), os.Getenv("ANNEX_VENDOR_URL"))
	address := ":" + os.Getenv("PORT")
	log.Printf("listening on %s", address)
	log.Fatal(http.ListenAndServe(address, newServer(desks, vendors)))
}

// vendorsAt is every vendor of rooms, each at its base URL.
func vendorsAt(roomVendorURL, annexVendorURL string) []rooms.Source {
	return []rooms.Source{rooms.NewRoomVendor(roomVendorURL), rooms.NewAnnexVendor(annexVendorURL)}
}
