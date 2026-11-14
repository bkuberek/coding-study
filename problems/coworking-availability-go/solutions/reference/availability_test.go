package main

import (
	"context"
	"errors"
	"net/http"
	"reflect"
	"testing"
	"time"

	"coworking/internal/rooms"
)

// fixedVendor answers the same slots, or the same failure, every time.
type fixedVendor struct {
	name  string
	slots []rooms.Slot
	err   error
}

func (v fixedVendor) Name() string {
	return v.name
}

func (v fixedVendor) OpenSlots(context.Context, time.Time) ([]rooms.Slot, error) {
	return v.slots, v.err
}

var march8 = time.Date(2027, time.March, 8, 0, 0, 0, 0, time.UTC)

func slot(room, start, end, vendor string) rooms.Slot {
	return rooms.Slot{Room: room, Start: start, End: end, Vendor: vendor}
}

func TestTheSlotsOfEveryVendorAreSortedByStartThenRoom(t *testing.T) {
	early, nine, oak := slot("A1", "08:00", "08:45", "a"), slot("A2", "09:00", "10:00", "a"), slot("oak", "09:00", "10:00", "b")
	vendors := []rooms.Source{
		fixedVendor{name: "b", slots: []rooms.Slot{oak}},
		fixedVendor{name: "a", slots: []rooms.Slot{nine, early}},
	}

	found := askEveryVendor(context.Background(), march8, vendors)

	want := []rooms.Slot{early, nine, oak}
	if !reflect.DeepEqual(found.Slots, want) {
		t.Errorf("slots %v, want %v", found.Slots, want)
	}
}

func TestAVendorThatFailsCostsOnlyItsOwnSlots(t *testing.T) {
	kept := []rooms.Slot{slot("A1", "08:00", "08:45", "annex")}
	vendors := []rooms.Source{
		fixedVendor{name: "rooms", err: errors.New("down")},
		fixedVendor{name: "annex", slots: kept},
	}

	found := askEveryVendor(context.Background(), march8, vendors)

	want := roomAvailability{Slots: kept, Unavailable: []string{"rooms"}}
	if !reflect.DeepEqual(found, want) {
		t.Errorf("found %+v, want %+v", found, want)
	}
}

func TestEveryVendorDownLeavesTwoEmptyListsRatherThanNone(t *testing.T) {
	vendors := []rooms.Source{
		fixedVendor{name: "rooms", err: errors.New("down")},
		fixedVendor{name: "annex", err: errors.New("closed")},
	}

	found := askEveryVendor(context.Background(), march8, vendors)

	want := roomAvailability{Slots: []rooms.Slot{}, Unavailable: []string{"annex", "rooms"}}
	if !reflect.DeepEqual(found, want) {
		t.Errorf("found %+v, want %+v", found, want)
	}
}

func roomsOn(t *testing.T, day string) any {
	t.Helper()
	status, body := get(t, app(t), "/availability?date="+day)
	if status != http.StatusOK {
		t.Fatalf("GET /availability?date=%s answered %d", day, status)
	}
	return body.(map[string]any)["rooms"]
}

func TestBothVendorsAnswerInOneList(t *testing.T) {
	t.Cleanup(func() { resetVendors(t) })

	found := roomsOn(t, "2027-03-08").(map[string]any)

	if slots := found["slots"].([]any); len(slots) != 5 {
		t.Errorf("%d slots, want 5: %v", len(slots), slots)
	}
	if unavailable := found["unavailable"].([]any); len(unavailable) != 0 {
		t.Errorf("unavailable %v, want none", unavailable)
	}
}

func TestBothVendorsDownStillAnswerTheDesks(t *testing.T) {
	t.Cleanup(func() { resetVendors(t) })
	setScenario(t, "room-vendor", "outage")
	setScenario(t, "annex-vendor", "maintenance")

	found := roomsOn(t, "2027-03-08")

	want := fromJSON(t, `{"slots": [], "unavailable": ["annex-vendor", "room-vendor"]}`)
	if !reflect.DeepEqual(found, want) {
		t.Errorf("rooms %v, want %v", found, want)
	}
}
