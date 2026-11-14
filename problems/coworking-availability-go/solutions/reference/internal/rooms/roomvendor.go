package rooms

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"regexp"
	"strconv"
	"time"
)

const (
	roomVendorName        = "room-vendor"
	roomVendorMaxRequests = 3
	shortWait             = 200 * time.Millisecond
	openSlot              = "open"
)

var wholeSeconds = regexp.MustCompile(`^[0-9]{1,9}$`)

// RoomVendor sells the main building's rooms. It speaks in statuses and headers, and lists its
// slots by room.
type RoomVendor struct {
	availability string
	client       *http.Client
}

// NewRoomVendor is the room vendor at baseURL.
func NewRoomVendor(baseURL string) RoomVendor {
	return RoomVendor{availability: baseURL + "/v1/rooms/availability", client: &http.Client{}}
}

func (RoomVendor) Name() string {
	return roomVendorName
}

func (v RoomVendor) OpenSlots(ctx context.Context, day time.Time) ([]Slot, error) {
	url := v.availability + "?date=" + day.Format(time.DateOnly)
	send := func() (answer, error) { return get(ctx, v.client, url) }
	found, err := ask(ctx, send, roomVendorWaitBeforeRetry, roomVendorMaxRequests)
	if err != nil {
		return nil, err
	}
	if !found.ok() {
		return nil, fmt.Errorf("%s answered %d", roomVendorName, found.status)
	}
	var body roomVendorBody
	if err := json.Unmarshal(found.body, &body); err != nil {
		return nil, undocumented(roomVendorName, "no JSON")
	}
	return body.openSlots()
}

// roomVendorWaitBeforeRetry is how long to wait before asking again, and false when asking
// again will not help.
func roomVendorWaitBeforeRetry(found answer) (time.Duration, bool) {
	switch {
	case found.status == http.StatusTooManyRequests:
		seconds := found.header.Get("Retry-After")
		if !wholeSeconds.MatchString(seconds) {
			return shortWait, true
		}
		count, _ := strconv.Atoi(seconds)
		return time.Duration(count) * time.Second, true
	case found.status >= http.StatusInternalServerError:
		return shortWait, true
	default:
		return 0, false
	}
}

// roomVendorBody is the vendor's answer as its API documents it. A list left out decodes as
// nil, unlike an empty one, which is how a missing part shows.
type roomVendorBody struct {
	Rooms []struct {
		ID    string `json:"id"`
		Slots []struct {
			Status string `json:"status"`
			Start  string `json:"start"`
			End    string `json:"end"`
		} `json:"slots"`
	} `json:"rooms"`
}

// openSlots is the slots that can be booked, flattened, or an error for a part the vendor's API
// promises and the body leaves out. A slot that is not open may leave out its times.
func (b roomVendorBody) openSlots() ([]Slot, error) {
	if b.Rooms == nil {
		return nil, undocumented(roomVendorName, "no rooms")
	}
	slots := []Slot{}
	for _, room := range b.Rooms {
		if room.ID == "" || room.Slots == nil {
			return nil, undocumented(roomVendorName, "a room with no id or no slots")
		}
		for _, slot := range room.Slots {
			if slot.Status == "" {
				return nil, undocumented(roomVendorName, "a slot with no status")
			}
			if slot.Status != openSlot {
				continue
			}
			if slot.Start == "" || slot.End == "" {
				return nil, undocumented(roomVendorName, "an open slot with no times")
			}
			slots = append(slots, Slot{room.ID, slot.Start, slot.End, roomVendorName})
		}
	}
	return slots, nil
}
