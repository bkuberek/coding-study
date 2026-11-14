package transactional_kv_store

import "sort"

// remembered is a value a key held before a transaction first changed it; present is false when
// the key did not exist.
type remembered struct {
	value   string
	present bool
}

// version is a permanent value of a key as of a sequence number; present is false for a removal.
type version struct {
	sequence int
	value    string
	present  bool
}

type TransactionalStore struct {
	data   map[string]string // the current view, open transactions included
	counts map[string]int
	// undo holds one log per open transaction, innermost last: key -> value before its first change.
	undo []map[string]remembered
	// history lists the permanent values per key. A commit or an outside write advances the
	// sequence, and a snapshot remembers the sequence of its commit.
	history   map[string][]version
	sequence  int
	snapshots []int
}

func NewTransactionalStore() *TransactionalStore {
	return &TransactionalStore{
		data:    make(map[string]string),
		counts:  make(map[string]int),
		history: make(map[string][]version),
	}
}

// Level 1
func (s *TransactionalStore) Set(timestamp int64, key string, value string) {
	s.change(key, value, true)
}

// Level 1
func (s *TransactionalStore) Get(timestamp int64, key string) string {
	return s.data[key]
}

// Level 1
func (s *TransactionalStore) Remove(timestamp int64, key string) bool {
	if _, exists := s.data[key]; !exists {
		return false
	}
	s.change(key, "", false)
	return true
}

// Level 1
func (s *TransactionalStore) Count(timestamp int64, value string) int {
	return s.counts[value]
}

// Level 2
func (s *TransactionalStore) Begin(timestamp int64) {
	s.undo = append(s.undo, make(map[string]remembered))
}

// Level 2
func (s *TransactionalStore) Rollback(timestamp int64) bool {
	if len(s.undo) == 0 {
		return false
	}
	log := s.undo[len(s.undo)-1]
	s.undo = s.undo[:len(s.undo)-1]
	for key, previous := range log {
		s.assign(key, previous.value, previous.present)
	}
	return true
}

// Level 3
func (s *TransactionalStore) Depth(timestamp int64) int {
	return len(s.undo)
}

// Level 4
func (s *TransactionalStore) Commit(timestamp int64) int {
	if len(s.undo) == 0 {
		return -1
	}
	changed := s.undo[len(s.undo)-1]
	s.undo = s.undo[:len(s.undo)-1]
	if len(s.undo) > 0 {
		enclosing := s.undo[len(s.undo)-1]
		for key, previous := range changed {
			if _, seen := enclosing[key]; !seen {
				enclosing[key] = previous
			}
		}
		return 0
	}
	keys := make([]string, 0, len(changed))
	for key := range changed {
		keys = append(keys, key)
	}
	s.makePermanent(keys)
	s.snapshots = append(s.snapshots, s.sequence)
	return len(s.snapshots)
}

// Level 4
func (s *TransactionalStore) GetSnapshot(timestamp int64, version int, key string) string {
	if version < 1 || version > len(s.snapshots) {
		return ""
	}
	history := s.history[key]
	sequence := s.snapshots[version-1]
	position := sort.Search(len(history), func(i int) bool { return history[i].sequence > sequence })
	if position == 0 {
		return ""
	}
	return history[position-1].value
}

func (s *TransactionalStore) change(key, value string, present bool) {
	if len(s.undo) == 0 {
		s.assign(key, value, present)
		s.makePermanent([]string{key})
		return
	}
	log := s.undo[len(s.undo)-1]
	if _, seen := log[key]; !seen {
		previous, existed := s.data[key]
		log[key] = remembered{previous, existed}
	}
	s.assign(key, value, present)
}

func (s *TransactionalStore) assign(key, value string, present bool) {
	if previous, existed := s.data[key]; existed {
		s.counts[previous]--
	}
	if !present {
		delete(s.data, key)
		return
	}
	s.data[key] = value
	s.counts[value]++
}

func (s *TransactionalStore) makePermanent(keys []string) {
	s.sequence++
	for _, key := range keys {
		value, present := s.data[key]
		s.history[key] = append(s.history[key], version{s.sequence, value, present})
	}
}
