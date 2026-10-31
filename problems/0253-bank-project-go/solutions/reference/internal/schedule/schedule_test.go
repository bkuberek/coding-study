package schedule_test

import (
	"slices"
	"testing"

	"bank-project-go/internal/schedule"
)

// amounts lists the amounts of transfers, which these tests use as labels.
func amounts(transfers []schedule.Transfer) []int64 {
	labels := make([]int64, len(transfers))
	for i, t := range transfers {
		labels[i] = t.Amount
	}
	return labels
}

func TestTakeDueRunOrder(t *testing.T) {
	tests := []struct {
		name string
		due  []int64 // the due time of each booking, in booking order; booking k moves k
		now  int64
		want []int64
	}{
		{name: "earliest due first", due: []int64{30, 10, 20}, now: 30, want: []int64{2, 3, 1}},
		{name: "equal due times in booking order", due: []int64{40, 40, 40}, now: 40, want: []int64{1, 2, 3}},
		{name: "a tie survives an earlier booking", due: []int64{40, 40, 40, 33}, now: 40, want: []int64{4, 1, 2, 3}},
		{name: "due exactly now", due: []int64{5}, now: 5, want: []int64{1}},
		{name: "nothing due yet", due: []int64{6, 7}, now: 5, want: []int64{}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := schedule.New()
			for k, due := range tt.due {
				s.Book(schedule.Transfer{Amount: int64(k + 1), Due: due})
			}
			if got := amounts(s.TakeDue(tt.now)); !slices.Equal(got, tt.want) {
				t.Errorf("TakeDue(%d) amounts = %v, want %v", tt.now, got, tt.want)
			}
		})
	}
}

func TestTakeDueHandsOutEachTransferOnce(t *testing.T) {
	s := schedule.New()
	s.Book(schedule.Transfer{Amount: 1, Due: 10})
	s.TakeDue(10)
	if got := s.TakeDue(20); len(got) != 0 {
		t.Errorf("second TakeDue = %v, want nothing", got)
	}
}

func TestBookNumbersFromOne(t *testing.T) {
	s := schedule.New()
	got := []string{s.Book(schedule.Transfer{Due: 9}), s.Book(schedule.Transfer{Due: 1})}
	if want := []string{"transfer1", "transfer2"}; !slices.Equal(got, want) {
		t.Errorf("Book ids = %v, want %v", got, want)
	}
}

func TestCancelledTransferNeverRuns(t *testing.T) {
	s := schedule.New()
	id := s.Book(schedule.Transfer{Amount: 1, Due: 10})
	s.Book(schedule.Transfer{Amount: 2, Due: 10})
	s.Cancel(id)
	if got := amounts(s.TakeDue(10)); !slices.Equal(got, []int64{2}) {
		t.Errorf("TakeDue after Cancel amounts = %v, want [2]", got)
	}
}

func TestCancelOnlyWhilePending(t *testing.T) {
	tests := []struct {
		name   string
		before func(s *schedule.Scheduler, id string)
		id     string
		want   bool
	}{
		{name: "pending", before: func(*schedule.Scheduler, string) {}, id: "transfer1", want: true},
		{name: "already cancelled", before: func(s *schedule.Scheduler, id string) { s.Cancel(id) }, id: "transfer1"},
		{name: "already handed out", before: func(s *schedule.Scheduler, _ string) { s.TakeDue(10) }, id: "transfer1"},
		{name: "unknown id", before: func(*schedule.Scheduler, string) {}, id: "transfer01"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := schedule.New()
			id := s.Book(schedule.Transfer{Amount: 1, Due: 10})
			tt.before(s, id)
			if got := s.Cancel(tt.id); got != tt.want {
				t.Errorf("Cancel(%q) = %v, want %v", tt.id, got, tt.want)
			}
		})
	}
}

func TestPendingReturnsTheBookedTransfer(t *testing.T) {
	s := schedule.New()
	booked := schedule.Transfer{Source: "a", Target: "b", Amount: 5, Due: 10}
	id := s.Book(booked)
	if got, ok := s.Pending(id); !ok || got != booked {
		t.Errorf("Pending(%q) = %v, %v, want %v, true", id, got, ok, booked)
	}
}
