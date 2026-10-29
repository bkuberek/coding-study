package time_based_kv_store

// entry is one write: the value a key got at a timestamp.
type entry struct {
	timestamp int
	value     string
}

type TimeMap struct {
	// Per key, the writes in the order they happened (timestamps strictly increase).
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
	for i := len(entries) - 1; i >= 0; i-- {
		if entries[i].timestamp <= timestamp {
			return entries[i].value
		}
	}
	return ""
}
