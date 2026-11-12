package crdt_replicas

import (
	"sort"
	"strconv"
)

// slot is one replica's slot of a counter: what it added (up) and what it took away (down), each
// with the change number at which it last grew.
type counterSlot struct {
	up, upAt, down, downAt int64
}

type lwwRegister struct {
	text      string
	timestamp int64
	writer    string
	at        int64
}

func (r *lwwRegister) losesTo(timestamp int64, writer string) bool {
	if timestamp != r.timestamp {
		return timestamp > r.timestamp
	}
	return writer > r.writer
}

type addTag struct {
	addedAt   int64
	removed   bool
	removedAt int64
}

// replica is the whole state of one replica. Every entry (a counter slot's up or down part, a
// register, an add tag, a tombstone) only grows, and each one remembers the change number at
// which it last grew, so a sync can pick the entries that changed after the last acknowledgement.
type replicaState struct {
	clock     int64
	adds      int
	counters  map[string]map[string]*counterSlot
	registers map[string]*lwwRegister
	sets      map[string]map[string]map[string]*addTag
	acked     map[string]int64
}

func newReplica() *replicaState {
	return &replicaState{
		counters:  map[string]map[string]*counterSlot{},
		registers: map[string]*lwwRegister{},
		sets:      map[string]map[string]map[string]*addTag{},
		acked:     map[string]int64{},
	}
}

func (r *replicaState) tick() int64 {
	r.clock++
	return r.clock
}

func (r *replicaState) slot(counter, owner string) *counterSlot {
	slots, ok := r.counters[counter]
	if !ok {
		slots = map[string]*counterSlot{}
		r.counters[counter] = slots
	}
	s, ok := slots[owner]
	if !ok {
		s = &counterSlot{}
		slots[owner] = s
	}
	return s
}

func (r *replicaState) total(counter string) int {
	var sum int64
	for _, s := range r.counters[counter] {
		sum += s.up - s.down
	}
	return int(sum)
}

func (r *replicaState) tags(setName, element string) map[string]*addTag {
	elements, ok := r.sets[setName]
	if !ok {
		elements = map[string]map[string]*addTag{}
		r.sets[setName] = elements
	}
	tags, ok := elements[element]
	if !ok {
		tags = map[string]*addTag{}
		elements[element] = tags
	}
	return tags
}

func (r *replicaState) live(setName, element string) bool {
	for _, t := range r.sets[setName][element] {
		if !t.removed {
			return true
		}
	}
	return false
}

func (r *replicaState) size() int {
	count := len(r.registers)
	for _, slots := range r.counters {
		for _, s := range slots {
			if s.up > 0 {
				count++
			}
			if s.down > 0 {
				count++
			}
		}
	}
	for _, elements := range r.sets {
		for _, tags := range elements {
			for _, t := range tags {
				count++
				if t.removed {
					count++
				}
			}
		}
	}
	return count
}

// absorb joins every entry of source that changed after since and returns how many entries that
// was. since = 0 is a full-state merge.
func (r *replicaState) absorb(source *replicaState, since int64) int {
	sent := 0
	for counter, slots := range source.counters {
		for owner, theirs := range slots {
			mine := r.slot(counter, owner)
			if theirs.up > 0 && theirs.upAt > since {
				sent++
				if theirs.up > mine.up {
					mine.up, mine.upAt = theirs.up, r.tick()
				}
			}
			if theirs.down > 0 && theirs.downAt > since {
				sent++
				if theirs.down > mine.down {
					mine.down, mine.downAt = theirs.down, r.tick()
				}
			}
		}
	}
	for name, theirs := range source.registers {
		if theirs.at <= since {
			continue
		}
		sent++
		mine, ok := r.registers[name]
		if !ok || mine.losesTo(theirs.timestamp, theirs.writer) {
			r.registers[name] = &lwwRegister{theirs.text, theirs.timestamp, theirs.writer, r.tick()}
		}
	}
	for setName, elements := range source.sets {
		for element, tags := range elements {
			mine := r.tags(setName, element)
			for id, theirs := range tags {
				sent += r.absorbTag(mine, id, theirs, since)
			}
		}
	}
	return sent
}

func (r *replicaState) absorbTag(mine map[string]*addTag, id string, theirs *addTag, since int64) int {
	sent := 0
	if theirs.addedAt > since {
		sent++
		if _, ok := mine[id]; !ok {
			mine[id] = &addTag{addedAt: r.tick()}
		}
	}
	if theirs.removed && theirs.removedAt > since {
		sent++
		held, ok := mine[id]
		if !ok {
			held = &addTag{addedAt: r.tick()}
			mine[id] = held
		}
		if !held.removed {
			held.removed, held.removedAt = true, r.tick()
		}
	}
	return sent
}

// Replicas is a group of replicas of the same data. Each replica's state is a set of entries that
// only grow, and merging is taking the larger value of every entry, so merges can happen in any
// order, any number of times, and replicas that have seen the same updates hold the same state.
type Replicas struct {
	replicas map[string]*replicaState
}

func NewReplicas(ids []string) *Replicas {
	all := map[string]*replicaState{}
	for _, id := range ids {
		all[id] = newReplica()
	}
	return &Replicas{replicas: all}
}

// Level 1
func (g *Replicas) Increment(replica string, counter string, amount int) int {
	node := g.replicas[replica]
	s := node.slot(counter, replica)
	s.up, s.upAt = s.up+int64(amount), node.tick()
	return node.total(counter)
}

func (g *Replicas) Decrement(replica string, counter string, amount int) int {
	node := g.replicas[replica]
	s := node.slot(counter, replica)
	s.down, s.downAt = s.down+int64(amount), node.tick()
	return node.total(counter)
}

func (g *Replicas) Value(replica string, counter string) int {
	return g.replicas[replica].total(counter)
}

func (g *Replicas) Merge(source string, target string) {
	g.replicas[target].absorb(g.replicas[source], 0)
}

// Level 2
func (g *Replicas) Write(replica string, register string, text string, timestamp int64) bool {
	node := g.replicas[replica]
	if current, ok := node.registers[register]; ok && !current.losesTo(timestamp, replica) {
		return false
	}
	node.registers[register] = &lwwRegister{text, timestamp, replica, node.tick()}
	return true
}

func (g *Replicas) Read(replica string, register string) string {
	if current, ok := g.replicas[replica].registers[register]; ok {
		return current.text
	}
	return ""
}

// Level 3
func (g *Replicas) Add(replica string, setName string, element string) string {
	node := g.replicas[replica]
	node.adds++
	id := replica + ":" + strconv.Itoa(node.adds)
	node.tags(setName, element)[id] = &addTag{addedAt: node.tick()}
	return id
}

func (g *Replicas) Remove(replica string, setName string, element string) int {
	node := g.replicas[replica]
	removed := 0
	for _, t := range node.sets[setName][element] {
		if !t.removed {
			t.removed, t.removedAt = true, node.tick()
			removed++
		}
	}
	return removed
}

func (g *Replicas) Contains(replica string, setName string, element string) bool {
	return g.replicas[replica].live(setName, element)
}

func (g *Replicas) Elements(replica string, setName string) []string {
	node := g.replicas[replica]
	present := []string{}
	for element := range node.sets[setName] {
		if node.live(setName, element) {
			present = append(present, element)
		}
	}
	sort.Strings(present)
	return present
}

// Level 4
func (g *Replicas) Sync(source string, target string) int {
	sender := g.replicas[source]
	sent := g.replicas[target].absorb(sender, sender.acked[target])
	sender.acked[target] = sender.clock
	return sent
}

func (g *Replicas) StateSize(replica string) int {
	return g.replicas[replica].size()
}
