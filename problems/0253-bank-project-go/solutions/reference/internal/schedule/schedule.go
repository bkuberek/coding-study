// Package schedule books transfers to run at a later time and hands them out in the order
// they fall due. It knows account ids, never accounts: what running a transfer means is the
// bank's business.
package schedule

import (
	"container/heap"
	"strconv"
)

// Transfer is money booked to move from Source to Target at time Due. Source and Target are
// the ids given at booking time; a merge may hand them to another account later.
type Transfer struct {
	Source string
	Target string
	Amount int64
	Due    int64
}

// booking is a booked transfer with its booking number. It is pending until it runs, is
// skipped or is cancelled.
type booking struct {
	Transfer
	number  int
	pending bool
}

// Scheduler numbers booked transfers and hands them out by due time, ties in booking order.
//
// A cancelled booking stays in the queue and is dropped when it reaches the front, since a
// heap can only remove its front cheaply.
type Scheduler struct {
	bookings map[string]*booking
	queue    queue
}

// New returns a scheduler with nothing booked.
func New() *Scheduler {
	return &Scheduler{bookings: map[string]*booking{}}
}

// Book queues t and returns its id, "transfer<k>" for the k-th booking.
func (s *Scheduler) Book(t Transfer) string {
	b := &booking{Transfer: t, number: len(s.bookings) + 1, pending: true}
	id := "transfer" + strconv.Itoa(b.number)
	s.bookings[id] = b
	heap.Push(&s.queue, b)
	return id
}

// Pending returns the transfer booked as id while it still waits to run.
func (s *Scheduler) Pending(id string) (Transfer, bool) {
	b, ok := s.bookings[id]
	if !ok || !b.pending {
		return Transfer{}, false
	}
	return b.Transfer, true
}

// Cancel withdraws the transfer booked as id, so it never runs; false when it is not
// pending.
func (s *Scheduler) Cancel(id string) bool {
	b, ok := s.bookings[id]
	if !ok || !b.pending {
		return false
	}
	b.pending = false
	return true
}

// TakeDue removes the pending transfers due at or before now from the queue and returns
// them in run order: by due time, ties in booking order.
func (s *Scheduler) TakeDue(now int64) []Transfer {
	var due []Transfer
	for s.queue.Len() > 0 && s.queue[0].Due <= now {
		b := heap.Pop(&s.queue).(*booking)
		if b.pending {
			b.pending = false
			due = append(due, b.Transfer)
		}
	}
	return due
}
