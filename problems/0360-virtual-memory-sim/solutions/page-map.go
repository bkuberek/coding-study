package virtual_memory_sim

import (
	"math/bits"
	"sort"
)

type tlbEntry struct {
	frame int64
	used  int64
}

// VirtualMemory is one address space: a page table from page to frame, an optional TLB, and,
// once demand paging is on, a frame table with the state each replacement policy needs. Go has
// no ordered map, so the TLB and the policies keep a stamp from a counter that grows with every
// event: the stamp of a TLB entry's last use, and the stamps of each page's load and last use.
// Evicting scans for the smallest stamp, which is cheap for at most 64 entries or frames. Every
// translation is one reference in a history, which the working set reads.
type VirtualMemory struct {
	size       int64
	shift      int
	table      map[int64]int64
	faultCount int
	tlb        map[int64]tlbEntry
	tlbOn      bool
	tlbEntries int
	hits       int
	misses     int
	frames     int
	policy     string
	owner      []int64
	loadedAt   map[int64]int64
	usedAt     map[int64]int64
	use        []bool
	hand       int
	now        int64
	history    []int64
}

func NewVirtualMemory(pageSize int) *VirtualMemory {
	return &VirtualMemory{
		size:     int64(pageSize),
		shift:    bits.TrailingZeros(uint(pageSize)),
		table:    map[int64]int64{},
		tlb:      map[int64]tlbEntry{},
		loadedAt: map[int64]int64{},
		usedAt:   map[int64]int64{},
	}
}

// Level 1

func (m *VirtualMemory) Split(address int64) []int64 {
	return []int64{address >> m.shift, address & (m.size - 1)}
}

func (m *VirtualMemory) MapPage(page int64, frame int64) bool {
	_, existed := m.table[page]
	m.table[page] = frame
	delete(m.tlb, page)
	return !existed
}

func (m *VirtualMemory) UnmapPage(page int64) bool {
	if _, ok := m.table[page]; !ok {
		return false
	}
	delete(m.table, page)
	delete(m.tlb, page)
	return true
}

func (m *VirtualMemory) Translate(address int64) int64 {
	page := address >> m.shift
	m.history = append(m.history, page)
	frame, ok := m.frameOf(page)
	if !ok {
		return -1
	}
	return frame*m.size + address&(m.size-1)
}

func (m *VirtualMemory) Faults() int {
	return m.faultCount
}

// Level 2

func (m *VirtualMemory) EnableTlb(entries int) {
	m.tlb = map[int64]tlbEntry{}
	m.tlbOn = true
	m.tlbEntries = entries
	m.hits, m.misses = 0, 0
}

func (m *VirtualMemory) FlushTlb() {
	m.tlb = map[int64]tlbEntry{}
}

func (m *VirtualMemory) TlbHits() int {
	return m.hits
}

func (m *VirtualMemory) TlbMisses() int {
	return m.misses
}

// Level 3

func (m *VirtualMemory) UseFrames(count int, policy string) {
	m.frames, m.policy = count, policy
	m.table = map[int64]int64{}
	m.FlushTlb()
	m.faultCount, m.hits, m.misses = 0, 0, 0
	m.owner = make([]int64, count)
	m.use = make([]bool, count)
	m.loadedAt = map[int64]int64{}
	m.usedAt = map[int64]int64{}
	m.hand = 0
	m.history = nil
}

func (m *VirtualMemory) Resident() []int64 {
	pages := make([]int64, 0, len(m.table))
	for page := range m.table {
		pages = append(pages, page)
	}
	sort.Slice(pages, func(i, j int) bool { return pages[i] < pages[j] })
	return pages
}

// Level 4

func (m *VirtualMemory) Walk(address int64, entryBytes int) []int64 {
	perTable := m.size / int64(entryBytes)
	page := address >> m.shift
	return []int64{page / perTable, page % perTable, address & (m.size - 1)}
}

func (m *VirtualMemory) TableBytes(addressBits int, entryBytes int) []int64 {
	pages := int64(1) << (addressBits - m.shift)
	perTable := m.size / int64(entryBytes)
	directory := pages / perTable * int64(entryBytes)
	tables := map[int64]bool{}
	for page := range m.table {
		tables[page/perTable] = true
	}
	return []int64{pages * int64(entryBytes), directory + int64(len(tables))*m.size}
}

func (m *VirtualMemory) WorkingSet(window int) []int64 {
	seen := map[int64]bool{}
	pages := []int64{}
	for _, page := range m.history[max(0, len(m.history)-window):] {
		if !seen[page] {
			seen[page] = true
			pages = append(pages, page)
		}
	}
	sort.Slice(pages, func(i, j int) bool { return pages[i] < pages[j] })
	return pages
}

func (m *VirtualMemory) Thrashing(window int) bool {
	return m.frames > 0 && len(m.WorkingSet(window)) > m.frames
}

// Translation

func (m *VirtualMemory) frameOf(page int64) (int64, bool) {
	m.now++
	if m.tlbOn {
		if entry, ok := m.tlb[page]; ok {
			m.hits++
			m.tlb[page] = tlbEntry{entry.frame, m.now}
			m.touch(page)
			return entry.frame, true
		}
		m.misses++
	}
	frame, ok := m.table[page]
	if !ok {
		m.faultCount++
		if m.frames == 0 {
			return 0, false
		}
		frame = m.load(page)
	}
	m.touch(page)
	if m.tlbOn {
		if len(m.tlb) == m.tlbEntries {
			oldest, first := int64(0), true
			for p, entry := range m.tlb {
				if first || entry.used < m.tlb[oldest].used {
					oldest, first = p, false
				}
			}
			delete(m.tlb, oldest)
		}
		m.tlb[page] = tlbEntry{frame, m.now}
	}
	return frame, true
}

func (m *VirtualMemory) touch(page int64) {
	if m.frames == 0 {
		return
	}
	m.usedAt[page] = m.now
	m.use[m.table[page]] = true
}

func (m *VirtualMemory) load(page int64) int64 {
	var frame int
	if len(m.table) < m.frames {
		frame = len(m.table)
	} else {
		frame = m.victimFrame()
		victim := m.owner[frame]
		delete(m.table, victim)
		delete(m.loadedAt, victim)
		delete(m.usedAt, victim)
		delete(m.tlb, victim)
	}
	m.table[page] = int64(frame)
	m.owner[frame] = page
	m.loadedAt[page] = m.now
	return int64(frame)
}

func (m *VirtualMemory) victimFrame() int {
	switch m.policy {
	case "fifo":
		return m.oldest(m.loadedAt)
	case "lru":
		return m.oldest(m.usedAt)
	}
	for m.use[m.hand] {
		m.use[m.hand] = false
		m.hand = (m.hand + 1) % m.frames
	}
	frame := m.hand
	m.hand = (m.hand + 1) % m.frames
	return frame
}

// oldest is the frame whose page has the smallest stamp.
func (m *VirtualMemory) oldest(stamp map[int64]int64) int {
	best := 0
	for f := 1; f < m.frames; f++ {
		if stamp[m.owner[f]] < stamp[m.owner[best]] {
			best = f
		}
	}
	return best
}
