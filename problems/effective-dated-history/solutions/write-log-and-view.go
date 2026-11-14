package effective_dated_history

import (
	"slices"
	"sort"
	"time"
)

type fieldHistory struct {
	// Every write, in timestamp order (timestamps are sorted and distinct).
	writeTimes  []int64
	writeDates  []time.Time
	writeValues []string
	// The current view: dates strictly ascending, one value per date. A correction replaces the
	// value for its date. There is no sorted map in the standard library.
	viewDates  []time.Time
	viewValues []string
}

func (h *fieldHistory) write(timestamp int64, effectiveDate time.Time, value string) {
	h.writeTimes = append(h.writeTimes, timestamp)
	h.writeDates = append(h.writeDates, effectiveDate)
	h.writeValues = append(h.writeValues, value)
	slot, found := slices.BinarySearchFunc(h.viewDates, effectiveDate, time.Time.Compare)
	if found {
		h.viewValues[slot] = value
	} else {
		h.viewDates = slices.Insert(h.viewDates, slot, effectiveDate)
		h.viewValues = slices.Insert(h.viewValues, slot, value)
	}
}

// current is the value of the last view entry on or before the day, or "" when there is none.
func (h *fieldHistory) current(onDate time.Time) string {
	slot := sort.Search(len(h.viewDates), func(i int) bool { return h.viewDates[i].After(onDate) }) - 1
	if slot < 0 {
		return ""
	}
	return h.viewValues[slot]
}

// asKnown replays the writes made at or before knownAt: the one with the latest effective date on
// or before the day wins, and a later write wins a tie on the date.
func (h *fieldHistory) asKnown(onDate time.Time, knownAt int64) string {
	known := sort.Search(len(h.writeTimes), func(i int) bool { return h.writeTimes[i] > knownAt })
	var bestDate time.Time
	bestValue := ""
	found := false
	for i := 0; i < known; i++ {
		effectiveDate := h.writeDates[i]
		// Not-before lets a later write for the same date replace an earlier one.
		if !effectiveDate.After(onDate) && (!found || !effectiveDate.Before(bestDate)) {
			bestDate = effectiveDate
			bestValue = h.writeValues[i]
			found = true
		}
	}
	return bestValue
}

type RecordHistory struct {
	records map[string]map[string]*fieldHistory
}

func NewRecordHistory() *RecordHistory {
	return &RecordHistory{records: make(map[string]map[string]*fieldHistory)}
}

func (h *RecordHistory) SetValue(timestamp int64, recordId string, field string, effectiveDate time.Time, value string) {
	fields, ok := h.records[recordId]
	if !ok {
		fields = make(map[string]*fieldHistory)
		h.records[recordId] = fields
	}
	history, ok := fields[field]
	if !ok {
		history = &fieldHistory{}
		fields[field] = history
	}
	history.write(timestamp, effectiveDate, value)
}

func (h *RecordHistory) GetValue(timestamp int64, recordId string, field string, onDate time.Time) string {
	if history := h.history(recordId, field); history != nil {
		return history.current(onDate)
	}
	return ""
}

func (h *RecordHistory) Snapshot(timestamp int64, recordId string, onDate time.Time) []string {
	return h.snapshotWith(recordId, func(history *fieldHistory) string { return history.current(onDate) })
}

func (h *RecordHistory) GetValueAsKnown(timestamp int64, recordId string, field string, onDate time.Time, knownAt int64) string {
	if history := h.history(recordId, field); history != nil {
		return history.asKnown(onDate, knownAt)
	}
	return ""
}

func (h *RecordHistory) SnapshotAsKnown(timestamp int64, recordId string, onDate time.Time, knownAt int64) []string {
	return h.snapshotWith(recordId, func(history *fieldHistory) string { return history.asKnown(onDate, knownAt) })
}

// history returns nil for an unknown record or field; a lookup in a nil map is safe in Go.
func (h *RecordHistory) history(recordId string, field string) *fieldHistory {
	return h.records[recordId][field]
}

func (h *RecordHistory) snapshotWith(recordId string, read func(*fieldHistory) string) []string {
	fields := h.records[recordId]
	names := make([]string, 0, len(fields))
	for name := range fields {
		names = append(names, name)
	}
	slices.Sort(names) // field names in text (byte) order
	entries := []string{}
	for _, name := range names {
		if value := read(fields[name]); value != "" {
			entries = append(entries, name+"="+value)
		}
	}
	return entries
}
