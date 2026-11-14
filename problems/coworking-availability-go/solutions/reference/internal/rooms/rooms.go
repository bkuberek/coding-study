// Package rooms asks the vendors that sell the meeting rooms, each in its own way, and gives
// every answer the same shape: the seam between the API and its vendors.
package rooms

import (
	"context"
	"fmt"
	"time"
)

// Slot is a time a room can be booked, and the vendor that sells it, since a booking goes there.
type Slot struct {
	Room   string `json:"room"`
	Start  string `json:"start"`
	End    string `json:"end"`
	Vendor string `json:"vendor"`
}

// Source is a vendor of rooms, whatever it speaks.
type Source interface {
	Name() string
	// OpenSlots is what can be booked on day, or an error when the vendor gives no usable
	// answer: none in time, a status that will not change, or a body its API does not document.
	OpenSlots(ctx context.Context, day time.Time) ([]Slot, error)
}

// undocumented is a body that is not what the vendor's API documents.
func undocumented(vendor, what string) error {
	return fmt.Errorf("%s sent %s, which its API does not document", vendor, what)
}
