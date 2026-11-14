package main

import (
	"cmp"
	"context"
	"log"
	"slices"
	"sync"
	"time"

	"coworking/internal/rooms"
)

// roomAvailability is one answer from every vendor, none of which can take another with it.
type roomAvailability struct {
	Slots       []rooms.Slot `json:"slots"`
	Unavailable []string     `json:"unavailable"`
}

type vendorAnswer struct {
	slots []rooms.Slot
	err   error
}

// askEveryVendor asks every vendor at once, each in a goroutine of its own, and waits for them
// all. A vendor with no usable answer goes in Unavailable; both lists are empty rather than nil,
// so they are written as [], and sorted.
func askEveryVendor(ctx context.Context, day time.Time, vendors []rooms.Source) roomAvailability {
	answers := make([]vendorAnswer, len(vendors))
	var asking sync.WaitGroup
	for index, vendor := range vendors {
		asking.Go(func() {
			slots, err := vendor.OpenSlots(ctx, day)
			answers[index] = vendorAnswer{slots, err}
		})
	}
	asking.Wait()
	found := roomAvailability{Slots: []rooms.Slot{}, Unavailable: []string{}}
	for index, answer := range answers {
		if answer.err != nil {
			log.Printf("%s is unavailable: %v", vendors[index].Name(), answer.err)
			found.Unavailable = append(found.Unavailable, vendors[index].Name())
			continue
		}
		found.Slots = append(found.Slots, answer.slots...)
	}
	slices.SortFunc(found.Slots, byStartThenRoom)
	slices.Sort(found.Unavailable)
	return found
}

func byStartThenRoom(first, second rooms.Slot) int {
	return cmp.Or(cmp.Compare(first.Start, second.Start), cmp.Compare(first.Room, second.Room))
}
