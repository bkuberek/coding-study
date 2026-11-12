package consistent_hash_ring

import (
	"slices"
	"sort"
	"strconv"
)

const ringSize int64 = 1 << 32

// fnv1a is FNV-1a, 32 bits, over the bytes of the text, which Go strings hold as UTF-8; uint32
// multiplication wraps at 32 bits.
func fnv1a(text string) int64 {
	value := uint32(2166136261)
	for i := 0; i < len(text); i++ {
		value ^= uint32(text[i])
		value *= 16777619
	}
	return int64(value)
}

// labelsOf names point 0 with the bare name and point i with "i#node": the number goes first,
// because FNV-1a mixes the first bytes of a text far better than its last ones.
func labelsOf(node string, count int) []string {
	labels := []string{node}
	for index := 1; index < count; index++ {
		labels = append(labels, strconv.Itoa(index)+"#"+node)
	}
	return labels
}

type point struct {
	position int64
	label    string
	node     string
}

func sortRing(ring []point) {
	sort.Slice(ring, func(i, j int) bool {
		if ring[i].position != ring[j].position {
			return ring[i].position < ring[j].position
		}
		return ring[i].label < ring[j].label
	})
}

// startOf is the index of the first point at or after the position, wrapping to 0 past the last.
func startOf(ring []point, position int64) int {
	index := sort.Search(len(ring), func(i int) bool { return ring[i].position >= position })
	if index == len(ring) {
		return 0
	}
	return index
}

func ownerIn(ring []point, position int64) string {
	if len(ring) == 0 {
		return ""
	}
	return ring[startOf(ring, position)].node
}

func moduloIn(order []string, key string) string {
	if len(order) == 0 {
		return ""
	}
	return order[fnv1a(key)%int64(len(order))]
}

// HashRing keeps its points in a slice sorted by position and then by label, which is the ring
// order with its tie-break. A key's owner is the first point at or after the key's position,
// found by binary search, wrapping to the first point.
type HashRing struct {
	points  []point
	joined  []string
	counts  map[string]int
	tracked map[string]bool
	report  [][]string
}

func NewHashRing() *HashRing {
	return &HashRing{counts: map[string]int{}, tracked: map[string]bool{}, report: [][]string{}}
}

// Level 1
func (r *HashRing) PositionOf(text string) int64 {
	return fnv1a(text)
}

func (r *HashRing) AddNode(node string) int64 {
	if !r.AddVirtualNode(node, 1) {
		return -1
	}
	return fnv1a(node)
}

func (r *HashRing) RemoveNode(node string) bool {
	if _, known := r.counts[node]; !known {
		return false
	}
	before := r.owners()
	kept := []point{}
	for _, p := range r.points {
		if p.node != node {
			kept = append(kept, p)
		}
	}
	r.points = kept
	r.joined = slices.DeleteFunc(r.joined, func(name string) bool { return name == node })
	delete(r.counts, node)
	r.makeReport(before)
	return true
}

func (r *HashRing) Nodes() []string {
	sorted := append([]string{}, r.joined...)
	sort.Strings(sorted)
	return sorted
}

func (r *HashRing) NodeFor(key string) string {
	return ownerIn(r.points, fnv1a(key))
}

func (r *HashRing) ModuloNodeFor(key string) string {
	return moduloIn(r.joined, key)
}

func (r *HashRing) CountMoves(keys []string, node string) []int {
	if _, known := r.counts[node]; known {
		return []int{}
	}
	grown := append(append([]point{}, r.points...), point{fnv1a(node), node, node})
	sortRing(grown)
	order := append(append([]string{}, r.joined...), node)
	ringMoves, moduloMoves := 0, 0
	for _, key := range keys {
		position := fnv1a(key)
		if ownerIn(r.points, position) != ownerIn(grown, position) {
			ringMoves++
		}
		if moduloIn(r.joined, key) != moduloIn(order, key) {
			moduloMoves++
		}
	}
	return []int{ringMoves, moduloMoves}
}

// Level 2
func (r *HashRing) AddVirtualNode(node string, count int) bool {
	if _, known := r.counts[node]; known || count < 1 {
		return false
	}
	before := r.owners()
	for _, label := range labelsOf(node, count) {
		r.points = append(r.points, point{fnv1a(label), label, node})
	}
	sortRing(r.points)
	r.joined = append(r.joined, node)
	r.counts[node] = count
	r.makeReport(before)
	return true
}

func (r *HashRing) Positions(node string) []int64 {
	found := []int64{}
	count, known := r.counts[node]
	if !known {
		return found
	}
	for _, label := range labelsOf(node, count) {
		found = append(found, fnv1a(label))
	}
	return found
}

func (r *HashRing) ArcShare() []int64 {
	share := map[string]int64{}
	for index, p := range r.points {
		previous := r.points[(index+len(r.points)-1)%len(r.points)].position
		arc := p.position - previous
		if index == 0 {
			arc += ringSize
		}
		share[p.node] += arc
	}
	answer := []int64{}
	for _, node := range r.Nodes() {
		answer = append(answer, share[node])
	}
	return answer
}

func (r *HashRing) KeyCounts(keys []string) []int {
	owned := map[string]int{}
	for _, key := range keys {
		owned[r.NodeFor(key)]++
	}
	answer := []int{}
	for _, node := range r.Nodes() {
		answer = append(answer, owned[node])
	}
	return answer
}

// Level 3
func (r *HashRing) TrackKeys(keys []string) int {
	for _, key := range keys {
		r.tracked[key] = true
	}
	return len(r.tracked)
}

func (r *HashRing) LastMoves() [][]string {
	copied := [][]string{}
	for _, row := range r.report {
		copied = append(copied, append([]string{}, row...))
	}
	return copied
}

func (r *HashRing) OwnedKeys(node string) []string {
	owned := []string{}
	if _, known := r.counts[node]; !known {
		return owned
	}
	for key := range r.tracked {
		if r.NodeFor(key) == node {
			owned = append(owned, key)
		}
	}
	sort.Strings(owned)
	return owned
}

// Level 4
func (r *HashRing) Replicas(key string, count int) []string {
	found := []string{}
	if count < 1 || len(r.points) == 0 {
		return found
	}
	start := startOf(r.points, fnv1a(key))
	for step := 0; step < len(r.points) && len(found) < count; step++ {
		node := r.points[(start+step)%len(r.points)].node
		if !slices.Contains(found, node) {
			found = append(found, node)
		}
	}
	return found
}

func (r *HashRing) AssignBounded(keys []string, numerator int, denominator int) []string {
	assigned := []string{}
	if len(r.points) == 0 || len(keys) == 0 {
		return assigned
	}
	total := (denominator + numerator) * len(keys)
	share := denominator * len(r.joined)
	capacity := (total + share - 1) / share
	load := map[string]int{}
	for _, key := range keys {
		index := startOf(r.points, fnv1a(key))
		for load[r.points[index].node] >= capacity {
			index = (index + 1) % len(r.points)
		}
		node := r.points[index].node
		load[node]++
		assigned = append(assigned, node)
	}
	return assigned
}

// Shared
func (r *HashRing) owners() map[string]string {
	owners := map[string]string{}
	for key := range r.tracked {
		owners[key] = r.NodeFor(key)
	}
	return owners
}

func (r *HashRing) makeReport(before map[string]string) {
	rows := [][]string{}
	for key, from := range before {
		if to := r.NodeFor(key); to != from {
			rows = append(rows, []string{key, from, to})
		}
	}
	sort.Slice(rows, func(i, j int) bool { return rows[i][0] < rows[j][0] })
	r.report = rows
}
