// In-Memory Database. Statement: .statements/in-memory-db.md. Run: cstudy test in-memory-db

package in_memory_db

type InMemoryDb struct{}

func NewInMemoryDb() *InMemoryDb {
	return &InMemoryDb{}
}

// Level 1
func (d *InMemoryDb) Set(timestamp int64, key string, field string, value string) {
	panic("not implemented")
}

// Level 1
func (d *InMemoryDb) Get(timestamp int64, key string, field string) string {
	panic("not implemented")
}

// Level 2
func (d *InMemoryDb) ScanByPrefix(timestamp int64, key string, prefix string) []string {
	panic("not implemented")
}
