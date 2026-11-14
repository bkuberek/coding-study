package btree_index

import (
	"slices"
	"strconv"
	"strings"
)

type node struct {
	leaf     bool
	keys     [][]int
	rows     []int
	children []*node
	next     *node
}

type step struct {
	parent *node
	index  int
}

// BTreeIndex is a B+ tree: every entry lives in a leaf, the leaves are linked left to right, and
// the inner nodes hold separator keys that only steer the way down. Keys are int slices compared
// field by field with slices.Compare. Every change walks down once and keeps the path, then
// repairs nodes on the way back up: splits after an insert, borrows and merges after a remove.
type BTreeIndex struct {
	d    int
	root *node
}

func NewBTreeIndex(minKeys int) *BTreeIndex {
	return &BTreeIndex{d: minKeys, root: &node{leaf: true}}
}

// Level 1

func (t *BTreeIndex) Search(key []int) int {
	leaf, _ := t.descend(key)
	at := lowerBound(leaf.keys, key)
	if holds(leaf, at, key) {
		return leaf.rows[at]
	}
	return -1
}

func (t *BTreeIndex) Insert(key []int, rowId int) bool {
	leaf, path := t.descend(key)
	at := lowerBound(leaf.keys, key)
	if holds(leaf, at, key) {
		return false
	}
	leaf.keys = slices.Insert(leaf.keys, at, slices.Clone(key))
	leaf.rows = slices.Insert(leaf.rows, at, rowId)
	t.splitUpward(leaf, path)
	return true
}

func (t *BTreeIndex) Levels() []string {
	lines := []string{}
	level := []*node{t.root}
	for len(level) > 0 {
		shown := make([]string, 0, len(level))
		var below []*node
		for _, n := range level {
			keys := make([]string, 0, len(n.keys))
			for _, key := range n.keys {
				fields := make([]string, len(key))
				for i, field := range key {
					fields[i] = strconv.Itoa(field)
				}
				keys = append(keys, strings.Join(fields, ","))
			}
			shown = append(shown, "["+strings.Join(keys, " ")+"]")
			below = append(below, n.children...)
		}
		lines = append(lines, strings.Join(shown, " "))
		level = below
	}
	return lines
}

// Level 2

func (t *BTreeIndex) RangeScan(low []int, high []int) []int {
	rows, _ := t.scan(low, high)
	return rows
}

func (t *BTreeIndex) ScanVisits(low []int, high []int) int {
	_, visits := t.scan(low, high)
	return visits
}

func (t *BTreeIndex) Height() int {
	count := 1
	for n := t.root; !n.leaf; n = n.children[0] {
		count++
	}
	return count
}

// Level 3

func (t *BTreeIndex) Remove(key []int) bool {
	leaf, path := t.descend(key)
	at := lowerBound(leaf.keys, key)
	if !holds(leaf, at, key) {
		return false
	}
	leaf.keys = slices.Delete(leaf.keys, at, at+1)
	leaf.rows = slices.Delete(leaf.rows, at, at+1)
	current := leaf
	for len(path) > 0 && len(current.keys) < t.d {
		last := path[len(path)-1]
		path = path[:len(path)-1]
		if current.leaf {
			t.fixLeaf(last.parent, last.index)
		} else {
			t.fixInner(last.parent, last.index)
		}
		current = last.parent
	}
	if !t.root.leaf && len(t.root.keys) == 0 {
		t.root = t.root.children[0]
	}
	return true
}

// Level 4

func (t *BTreeIndex) BulkLoad(keys [][]int, rowIds []int, fillPercent int) bool {
	if !t.root.leaf || len(t.root.keys) > 0 {
		return false
	}
	for i := 0; i+1 < len(keys); i++ {
		if slices.Compare(keys[i], keys[i+1]) >= 0 {
			return false
		}
	}
	if len(keys) == 0 {
		return true
	}
	per := 2 * t.d * fillPercent / 100
	var level []*node
	var lowest [][]int
	start := 0
	for _, size := range sizes(len(keys), per, t.d, 2*t.d) {
		leaf := &node{leaf: true}
		for i := start; i < start+size; i++ {
			leaf.keys = append(leaf.keys, slices.Clone(keys[i]))
			leaf.rows = append(leaf.rows, rowIds[i])
		}
		if len(level) > 0 {
			level[len(level)-1].next = leaf
		}
		level = append(level, leaf)
		lowest = append(lowest, leaf.keys[0])
		start += size
	}
	for len(level) > 1 {
		var parents []*node
		var parentLowest [][]int
		start = 0
		for _, size := range sizes(len(level), per+1, t.d+1, 2*t.d+1) {
			parent := &node{
				keys:     slices.Clone(lowest[start+1 : start+size]),
				children: slices.Clone(level[start : start+size]),
			}
			parents = append(parents, parent)
			parentLowest = append(parentLowest, lowest[start])
			start += size
		}
		level, lowest = parents, parentLowest
	}
	t.root = level[0]
	return true
}

func (t *BTreeIndex) PrefixScan(prefix []int) []int {
	width := len(prefix)
	current := t.root
	for !current.leaf {
		index := 0
		for _, separator := range current.keys {
			if slices.Compare(separator[:width], prefix) < 0 {
				index++
			}
		}
		current = current.children[index]
	}
	rows := []int{}
	for leaf := current; leaf != nil; leaf = leaf.next {
		for i, key := range leaf.keys {
			order := slices.Compare(key[:width], prefix)
			if order > 0 {
				return rows
			}
			if order == 0 {
				rows = append(rows, leaf.rows[i])
			}
		}
	}
	return rows
}

// Helpers

func (t *BTreeIndex) descend(key []int) (*node, []step) {
	var path []step
	current := t.root
	for !current.leaf {
		index := upperBound(current.keys, key)
		path = append(path, step{current, index})
		current = current.children[index]
	}
	return current, path
}

func holds(leaf *node, at int, key []int) bool {
	return at < len(leaf.keys) && slices.Compare(leaf.keys[at], key) == 0
}

// lowerBound is the first position whose key is at least key.
func lowerBound(keys [][]int, key []int) int {
	low, high := 0, len(keys)
	for low < high {
		middle := (low + high) / 2
		if slices.Compare(keys[middle], key) < 0 {
			low = middle + 1
		} else {
			high = middle
		}
	}
	return low
}

// upperBound is the number of keys that are at most key.
func upperBound(keys [][]int, key []int) int {
	low, high := 0, len(keys)
	for low < high {
		middle := (low + high) / 2
		if slices.Compare(keys[middle], key) <= 0 {
			low = middle + 1
		} else {
			high = middle
		}
	}
	return low
}

func (t *BTreeIndex) splitUpward(leaf *node, path []step) {
	d := t.d
	if len(leaf.keys) <= 2*d {
		return
	}
	// Copy the right halves before truncating, so the two nodes never share a backing array.
	right := &node{leaf: true, keys: slices.Clone(leaf.keys[d:]), rows: slices.Clone(leaf.rows[d:])}
	leaf.keys, leaf.rows = leaf.keys[:d:d], leaf.rows[:d:d]
	right.next, leaf.next = leaf.next, right
	left, separator, created := leaf, right.keys[0], right
	for len(path) > 0 {
		last := path[len(path)-1]
		path = path[:len(path)-1]
		parent := last.parent
		parent.keys = slices.Insert(parent.keys, last.index, separator)
		parent.children = slices.Insert(parent.children, last.index+1, created)
		if len(parent.keys) <= 2*d {
			return
		}
		separator = parent.keys[d]
		sibling := &node{keys: slices.Clone(parent.keys[d+1:]), children: slices.Clone(parent.children[d+1:])}
		parent.keys, parent.children = parent.keys[:d:d], parent.children[:d+1:d+1]
		left, created = parent, sibling
	}
	t.root = &node{keys: [][]int{separator}, children: []*node{left, created}}
}

func (t *BTreeIndex) scan(low []int, high []int) ([]int, int) {
	leaf, path := t.descend(low)
	visits := len(path) + 1
	rows := []int{}
	at := lowerBound(leaf.keys, low)
	for {
		for ; at < len(leaf.keys); at++ {
			if slices.Compare(leaf.keys[at], high) > 0 {
				return rows, visits
			}
			rows = append(rows, leaf.rows[at])
		}
		if leaf.next == nil {
			return rows, visits
		}
		leaf, at, visits = leaf.next, 0, visits+1
	}
}

func (t *BTreeIndex) siblings(parent *node, index int) (*node, *node) {
	var left, right *node
	if index > 0 {
		left = parent.children[index-1]
	}
	if index+1 < len(parent.children) {
		right = parent.children[index+1]
	}
	return left, right
}

func (t *BTreeIndex) fixLeaf(parent *node, index int) {
	current := parent.children[index]
	left, right := t.siblings(parent, index)
	switch {
	case left != nil && len(left.keys) > t.d:
		last := len(left.keys) - 1
		current.keys = slices.Insert(current.keys, 0, left.keys[last])
		current.rows = slices.Insert(current.rows, 0, left.rows[last])
		left.keys, left.rows = left.keys[:last], left.rows[:last]
		parent.keys[index-1] = current.keys[0]
	case right != nil && len(right.keys) > t.d:
		current.keys = append(current.keys, right.keys[0])
		current.rows = append(current.rows, right.rows[0])
		right.keys, right.rows = slices.Delete(right.keys, 0, 1), slices.Delete(right.rows, 0, 1)
		parent.keys[index] = right.keys[0]
	case left != nil:
		left.keys = append(left.keys, current.keys...)
		left.rows = append(left.rows, current.rows...)
		left.next = current.next
		parent.keys = slices.Delete(parent.keys, index-1, index)
		parent.children = slices.Delete(parent.children, index, index+1)
	default:
		current.keys = append(current.keys, right.keys...)
		current.rows = append(current.rows, right.rows...)
		current.next = right.next
		parent.keys = slices.Delete(parent.keys, index, index+1)
		parent.children = slices.Delete(parent.children, index+1, index+2)
	}
}

func (t *BTreeIndex) fixInner(parent *node, index int) {
	current := parent.children[index]
	left, right := t.siblings(parent, index)
	switch {
	case left != nil && len(left.keys) > t.d:
		last := len(left.keys) - 1
		current.keys = slices.Insert(current.keys, 0, parent.keys[index-1])
		current.children = slices.Insert(current.children, 0, left.children[last+1])
		parent.keys[index-1] = left.keys[last]
		left.keys, left.children = left.keys[:last], left.children[:last+1]
	case right != nil && len(right.keys) > t.d:
		current.keys = append(current.keys, parent.keys[index])
		current.children = append(current.children, right.children[0])
		parent.keys[index] = right.keys[0]
		right.keys, right.children = slices.Delete(right.keys, 0, 1), slices.Delete(right.children, 0, 1)
	case left != nil:
		left.keys = append(append(left.keys, parent.keys[index-1]), current.keys...)
		left.children = append(left.children, current.children...)
		parent.keys = slices.Delete(parent.keys, index-1, index)
		parent.children = slices.Delete(parent.children, index, index+1)
	default:
		current.keys = append(append(current.keys, parent.keys[index]), right.keys...)
		current.children = append(current.children, right.children...)
		parent.keys = slices.Delete(parent.keys, index, index+1)
		parent.children = slices.Delete(parent.children, index+1, index+2)
	}
}

func sizes(total, per, minimum, maximum int) []int {
	var result []int
	for i := 0; i < total/per; i++ {
		result = append(result, per)
	}
	if total%per != 0 {
		result = append(result, total%per)
	}
	if n := len(result); n > 1 && result[n-1] < minimum {
		pool := result[n-1] + result[n-2]
		result = result[:n-2]
		if pool <= maximum {
			result = append(result, pool)
		} else {
			result = append(result, (pool+1)/2, pool/2)
		}
	}
	return result
}
