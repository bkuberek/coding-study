package mvcc_snapshot_isolation

import (
	"slices"
	"sort"
	"strconv"
)

type transaction struct {
	start        int
	serializable bool
	state        string
	commitTime   int
	writes       map[string]string
	ins          map[int]bool
	outs         map[int]bool
}

type chain struct {
	stamps  []int
	values  []string
	writers []int
}

// before is the number of versions stamped before time.
func (c *chain) before(time int) int {
	return sort.SearchInts(c.stamps, time)
}

// MvccStore keeps, for every key, a chain of committed versions, oldest first, each stamped with
// the commit time of its writer and the id of that writer (0 for a put). A transaction buffers its
// writes until it commits, so the chains only ever hold committed data, and a read is a binary
// search for the newest stamp before the reader's start. Serializable transactions also leave
// their reads behind, even after they commit, and every read-write antidependency between two of
// them is kept as a pair of edges. An edge stops counting as soon as either end aborts.
type MvccStore struct {
	clock        int
	chains       map[string]*chain
	transactions map[int]*transaction
	readers      map[string]map[int]bool
}

func NewMvccStore() *MvccStore {
	return &MvccStore{
		chains:       map[string]*chain{},
		transactions: map[int]*transaction{},
		readers:      map[string]map[int]bool{},
	}
}

// Level 1

func (s *MvccStore) Put(key string, value string) int {
	s.clock++
	s.append(key, value, s.clock, 0)
	return s.clock
}

func (s *MvccStore) Begin() int {
	return s.start(false)
}

func (s *MvccStore) Read(tx int, key string) string {
	reader := s.active(tx)
	if reader == nil {
		return ""
	}
	if value, ok := reader.writes[key]; ok {
		return value
	}
	if reader.serializable && !s.recordRead(tx, reader, key) {
		return ""
	}
	c, ok := s.chains[key]
	if !ok {
		return ""
	}
	if visible := c.before(reader.start); visible > 0 {
		return c.values[visible-1]
	}
	return ""
}

func (s *MvccStore) Versions(key string) []string {
	listed := []string{}
	if c, ok := s.chains[key]; ok {
		for i := len(c.stamps) - 1; i >= 0; i-- {
			listed = append(listed, strconv.Itoa(c.stamps[i])+":"+c.values[i])
		}
	}
	return listed
}

// Level 2

func (s *MvccStore) Write(tx int, key string, value string) bool {
	writer := s.active(tx)
	if writer == nil {
		return false
	}
	if writer.serializable && !s.recordWrite(tx, writer, key) {
		return false
	}
	writer.writes[key] = value
	return true
}

func (s *MvccStore) Commit(tx int) string {
	t := s.active(tx)
	if t == nil {
		return "not-active"
	}
	for key := range t.writes {
		if c, ok := s.chains[key]; ok && c.stamps[len(c.stamps)-1] > t.start {
			t.state = "aborted"
			return "write-conflict"
		}
	}
	if t.serializable && len(s.live(t.ins)) > 0 && len(s.live(t.outs)) > 0 {
		t.state = "aborted"
		return "dangerous-structure"
	}
	s.clock++
	t.state, t.commitTime = "committed", s.clock
	for key, value := range t.writes {
		s.append(key, value, s.clock, tx)
	}
	return "committed"
}

func (s *MvccStore) Abort(tx int) bool {
	t := s.active(tx)
	if t == nil {
		return false
	}
	t.state = "aborted"
	return true
}

func (s *MvccStore) Status(tx int) string {
	if t, ok := s.transactions[tx]; ok {
		return t.state
	}
	return "unknown"
}

// Level 3

func (s *MvccStore) BeginSerializable() int {
	return s.start(true)
}

func (s *MvccStore) Antidependencies(tx int) []string {
	edges := []string{}
	t, ok := s.transactions[tx]
	if !ok || t.state == "aborted" {
		return edges
	}
	for _, other := range s.live(t.ins) {
		edges = append(edges, "in:"+strconv.Itoa(other))
	}
	for _, other := range s.live(t.outs) {
		edges = append(edges, "out:"+strconv.Itoa(other))
	}
	return edges
}

// Level 4

func (s *MvccStore) Horizon() int {
	oldest, found := s.clock, false
	for _, t := range s.transactions {
		if t.state == "active" && (!found || t.start < oldest) {
			oldest, found = t.start, true
		}
	}
	return oldest
}

func (s *MvccStore) Vacuum() []string {
	limit := s.Horizon()
	keys := make([]string, 0, len(s.chains))
	for key := range s.chains {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	removed := []string{}
	for _, key := range keys {
		c := s.chains[key]
		keepFrom := c.before(limit+1) - 1
		if keepFrom <= 0 {
			continue
		}
		for _, stamp := range c.stamps[:keepFrom] {
			removed = append(removed, key+"@"+strconv.Itoa(stamp))
		}
		c.stamps = slices.Clone(c.stamps[keepFrom:])
		c.values = slices.Clone(c.values[keepFrom:])
		c.writers = slices.Clone(c.writers[keepFrom:])
	}
	return removed
}

// Helpers

func (s *MvccStore) start(serializable bool) int {
	s.clock++
	s.transactions[s.clock] = &transaction{
		start:        s.clock,
		serializable: serializable,
		state:        "active",
		writes:       map[string]string{},
		ins:          map[int]bool{},
		outs:         map[int]bool{},
	}
	return s.clock
}

func (s *MvccStore) active(tx int) *transaction {
	if t, ok := s.transactions[tx]; ok && t.state == "active" {
		return t
	}
	return nil
}

func (s *MvccStore) append(key string, value string, stamp int, writer int) {
	c, ok := s.chains[key]
	if !ok {
		c = &chain{}
		s.chains[key] = c
	}
	c.stamps = append(c.stamps, stamp)
	c.values = append(c.values, value)
	c.writers = append(c.writers, writer)
}

func (s *MvccStore) takesPart(tx int) bool {
	t, ok := s.transactions[tx]
	return ok && t.serializable && t.state != "aborted"
}

// live returns the ids whose transaction has not aborted, sorted.
func (s *MvccStore) live(ids map[int]bool) []int {
	result := []int{}
	for other := range ids {
		if s.transactions[other].state != "aborted" {
			result = append(result, other)
		}
	}
	sort.Ints(result)
	return result
}

// recordRead: the reader misses every version committed after it began and every write still
// buffered by an active transaction, and each such writer gets an edge from the reader.
func (s *MvccStore) recordRead(tx int, reader *transaction, key string) bool {
	var missed []int
	if c, ok := s.chains[key]; ok {
		for _, writer := range c.writers[c.before(reader.start):] {
			if s.takesPart(writer) {
				if len(s.live(s.transactions[writer].outs)) > 0 {
					reader.state = "aborted"
					return false
				}
				missed = append(missed, writer)
			}
		}
	}
	for other, t := range s.transactions {
		if _, wrote := t.writes[key]; other != tx && t.serializable && t.state == "active" && wrote {
			missed = append(missed, other)
		}
	}
	if s.readers[key] == nil {
		s.readers[key] = map[int]bool{}
	}
	s.readers[key][tx] = true
	for _, writer := range missed {
		s.edge(tx, writer)
	}
	return true
}

// recordWrite: every reader of the key that overlaps the writer gets an edge to it.
func (s *MvccStore) recordWrite(tx int, writer *transaction, key string) bool {
	var overlapping []int
	for other := range s.readers[key] {
		t := s.transactions[other]
		if other == tx || !s.takesPart(other) {
			continue
		}
		if t.state == "active" || t.commitTime > writer.start {
			if t.state == "committed" && len(s.live(t.ins)) > 0 {
				writer.state = "aborted"
				return false
			}
			overlapping = append(overlapping, other)
		}
	}
	for _, reader := range overlapping {
		s.edge(reader, tx)
	}
	return true
}

func (s *MvccStore) edge(reader int, writer int) {
	s.transactions[reader].outs[writer] = true
	s.transactions[writer].ins[reader] = true
}
