package memory_allocator

import (
	"fmt"
	"slices"
)

const (
	header   = 8
	align    = 8
	minBlock = 16
)

var placementPolicies = []string{"first-fit", "next-fit", "best-fit"}

type block struct {
	start     int
	size      int
	used      bool
	requested int
}

// MemoryAllocator keeps the heap as a slice of blocks in address order, each with its start, its
// size (header included) and whether it is in use. Allocating splits a free block; freeing marks it
// free and, with coalescing or in the buddy system, merges it with its free neighbors. Next fit
// keeps a rover: the address where its next search starts.
type MemoryAllocator struct {
	heapSize   int
	blocks     []block
	coalescing bool
	policy     string
	started    bool
	rover      int
}

func NewMemoryAllocator(heapSize int) *MemoryAllocator {
	return &MemoryAllocator{
		heapSize: heapSize,
		blocks:   []block{{start: 0, size: heapSize}},
		policy:   "first-fit",
	}
}

// --- helpers

func (a *MemoryAllocator) position(start int) int {
	for i, b := range a.blocks {
		if b.start == start {
			return i
		}
	}
	return -1
}

func (a *MemoryAllocator) blockSize(size int) int {
	if a.policy == "buddy" {
		b := minBlock
		for b < size+header {
			b *= 2
		}
		return b
	}
	return header + (size+align-1)/align*align
}

// choose returns the position of the free block the policy picks, or -1.
func (a *MemoryAllocator) choose(need int) int {
	var fits []int
	for i, b := range a.blocks {
		if !b.used && b.size >= need {
			fits = append(fits, i)
		}
	}
	if len(fits) == 0 {
		return -1
	}
	switch a.policy {
	case "next-fit":
		here := a.position(a.rover)
		for _, i := range fits {
			if i >= here {
				return i
			}
		}
		return fits[0]
	case "best-fit", "buddy":
		best := fits[0]
		for _, i := range fits {
			if a.blocks[i].size < a.blocks[best].size {
				best = i
			}
		}
		return best
	default:
		return fits[0]
	}
}

func (a *MemoryAllocator) split(position, keep int) {
	b := &a.blocks[position]
	rest := block{start: b.start + keep, size: b.size - keep}
	b.size = keep
	a.blocks = slices.Insert(a.blocks, position+1, rest)
}

func (a *MemoryAllocator) mergeWithNext(position int) {
	following := a.blocks[position+1]
	a.blocks[position].size += following.size
	a.blocks = slices.Delete(a.blocks, position+1, position+2)
	if a.rover == following.start {
		a.rover = a.blocks[position].start
	}
}

func (a *MemoryAllocator) freeBuddies(position int) {
	for a.blocks[position].size < a.heapSize {
		b := a.blocks[position]
		other := a.position(b.start ^ b.size)
		if other < 0 || a.blocks[other].used || a.blocks[other].size != b.size {
			return
		}
		position = min(position, other)
		a.mergeWithNext(position)
	}
}

// Level 1

func (a *MemoryAllocator) Allocate(size int) int {
	a.started = true
	need := a.blockSize(size)
	position := a.choose(need)
	if position < 0 {
		return -1
	}
	if a.policy == "buddy" {
		for a.blocks[position].size > need {
			a.split(position, a.blocks[position].size/2)
		}
	} else if a.blocks[position].size-need >= minBlock {
		a.split(position, need)
	}
	b := &a.blocks[position]
	b.used = true
	b.requested = size
	a.rover = (b.start + b.size) % a.heapSize
	return b.start + header
}

func (a *MemoryAllocator) Free(address int) string {
	position := a.position(address - header)
	if position < 0 || !a.blocks[position].used {
		return "invalid"
	}
	a.blocks[position].used = false
	if a.policy == "buddy" {
		a.freeBuddies(position)
	} else if a.coalescing {
		if position+1 < len(a.blocks) && !a.blocks[position+1].used {
			a.mergeWithNext(position)
		}
		if position > 0 && !a.blocks[position-1].used {
			a.mergeWithNext(position - 1)
		}
	}
	return "ok"
}

func (a *MemoryAllocator) HeapMap() []string {
	lines := make([]string, len(a.blocks))
	for i, b := range a.blocks {
		state := "free"
		if b.used {
			state = "used"
		}
		lines[i] = fmt.Sprintf("%d %d %s", b.start, b.size, state)
	}
	return lines
}

// Level 2

func (a *MemoryAllocator) SetCoalescing(enabled bool) string {
	if a.started {
		return "too-late"
	}
	a.coalescing = enabled
	return "ok"
}

func (a *MemoryAllocator) FreeReport() []int {
	count, total, largest := 0, 0, 0
	for _, b := range a.blocks {
		if !b.used {
			count++
			total += b.size
			largest = max(largest, b.size)
		}
	}
	fragmentation := 0
	if total > 0 {
		fragmentation = 100 * (total - largest) / total
	}
	return []int{count, total, largest, fragmentation}
}

// Level 3

func (a *MemoryAllocator) SetPolicy(policy string) string {
	known := policy == "buddy"
	for _, name := range placementPolicies {
		known = known || policy == name
	}
	if !known {
		return "unknown-policy"
	}
	if a.started {
		return "too-late"
	}
	if policy == "buddy" && a.heapSize&(a.heapSize-1) != 0 {
		return "bad-size"
	}
	a.policy = policy
	return "ok"
}

func (a *MemoryAllocator) Compare(trace []int) [][]int {
	rows := make([][]int, 0, len(placementPolicies))
	for _, name := range placementPolicies {
		heap := NewMemoryAllocator(a.heapSize)
		heap.SetCoalescing(a.coalescing)
		heap.SetPolicy(name)
		var addresses []int
		failed := 0
		for _, step := range trace {
			if step > 0 {
				address := heap.Allocate(step)
				addresses = append(addresses, address)
				if address < 0 {
					failed++
				}
			} else if addresses[-step-1] >= 0 {
				heap.Free(addresses[-step-1])
			}
		}
		rows = append(rows, append([]int{failed}, heap.FreeReport()...))
	}
	return rows
}

// Level 4

func (a *MemoryAllocator) Wasted() int {
	total := 0
	for _, b := range a.blocks {
		if b.used {
			total += b.size - header - b.requested
		}
	}
	return total
}
