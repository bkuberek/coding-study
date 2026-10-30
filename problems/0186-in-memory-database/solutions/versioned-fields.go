package in_memory_database

import (
	"sort"
	"strings"
)

// version is one write to a field: a value (or a deletion), from since until expiresAt.
type version struct {
	since     int64
	value     string
	deleted   bool
	expiresAt int64
	expires   bool
}

func (v version) visibleAt(moment int64) bool {
	return !v.deleted && (!v.expires || moment < v.expiresAt)
}

// fieldHistory holds every version of one field, oldest first; timestamps arrive in increasing order.
type fieldHistory struct {
	versions []version
}

func (h *fieldHistory) valueAt(moment int64) (string, bool) {
	position := sort.Search(len(h.versions), func(i int) bool { return h.versions[i].since > moment })
	if position == 0 {
		return "", false
	}
	v := h.versions[position-1]
	if !v.visibleAt(moment) {
		return "", false
	}
	return v.value, true
}

type InMemoryDatabase struct {
	records map[string]map[string]*fieldHistory
}

func NewInMemoryDatabase() *InMemoryDatabase {
	return &InMemoryDatabase{records: make(map[string]map[string]*fieldHistory)}
}

// Level 1
func (d *InMemoryDatabase) Set(timestamp int64, key string, field string, value string) {
	d.write(key, field, version{since: timestamp, value: value})
}

// Level 1
func (d *InMemoryDatabase) Get(timestamp int64, key string, field string) string {
	value, _ := d.valueAt(key, field, timestamp)
	return value
}

// Level 1
func (d *InMemoryDatabase) Remove(timestamp int64, key string, field string) bool {
	if _, ok := d.valueAt(key, field, timestamp); !ok {
		return false
	}
	d.write(key, field, version{since: timestamp, deleted: true})
	return true
}

// Level 2
func (d *InMemoryDatabase) Scan(timestamp int64, key string) []string {
	return d.scan(key, "", timestamp)
}

// Level 2
func (d *InMemoryDatabase) ScanByPrefix(timestamp int64, key string, prefix string) []string {
	return d.scan(key, prefix, timestamp)
}

// Level 3
func (d *InMemoryDatabase) SetWithTtl(timestamp int64, key string, field string, value string, ttl int64) {
	d.write(key, field, version{since: timestamp, value: value, expiresAt: timestamp + ttl, expires: true})
}

// Level 4
func (d *InMemoryDatabase) GetAt(timestamp int64, key string, field string, atTimestamp int64) string {
	value, _ := d.valueAt(key, field, atTimestamp)
	return value
}

// Level 4
func (d *InMemoryDatabase) ScanAt(timestamp int64, key string, atTimestamp int64) []string {
	return d.scan(key, "", atTimestamp)
}

func (d *InMemoryDatabase) write(key, field string, v version) {
	fields, ok := d.records[key]
	if !ok {
		fields = make(map[string]*fieldHistory)
		d.records[key] = fields
	}
	history, ok := fields[field]
	if !ok {
		history = &fieldHistory{}
		fields[field] = history
	}
	history.versions = append(history.versions, v)
}

func (d *InMemoryDatabase) valueAt(key, field string, moment int64) (string, bool) {
	history, ok := d.records[key][field]
	if !ok {
		return "", false
	}
	return history.valueAt(moment)
}

func (d *InMemoryDatabase) scan(key, prefix string, moment int64) []string {
	type entry struct{ field, value string }
	var entries []entry
	for field, history := range d.records[key] {
		if !strings.HasPrefix(field, prefix) {
			continue
		}
		if value, ok := history.valueAt(moment); ok {
			entries = append(entries, entry{field, value})
		}
	}
	sort.Slice(entries, func(i, j int) bool { return entries[i].field < entries[j].field })
	lines := make([]string, len(entries))
	for i, e := range entries {
		lines[i] = e.field + "(" + e.value + ")"
	}
	return lines
}
