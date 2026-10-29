package time_based_kv_store

import "sort"

// entry is one write: the value a key got at a timestamp.
type entry struct {
	timestamp int
	value     string
}

type TimeMap struct {
	// Per key, the writes sorted by timestamp (they arrive in time order).
	history map[string][]entry
}

func NewTimeMap() *TimeMap {
	return &TimeMap{history: make(map[string][]entry)}
}

func (m *TimeMap) Set(key, value string, timestamp int) {
	m.history[key] = append(m.history[key], entry{timestamp, value})
}

func (m *TimeMap) Get(key string, timestamp int) string {
	entries := m.history[key]
	// Number of writes at or before timestamp; the last of them is the answer.
	count := sort.Search(len(entries), func(i int) bool { return entries[i].timestamp > timestamp })
	if count == 0 {
		return ""
	}
	return entries[count-1].value
}
