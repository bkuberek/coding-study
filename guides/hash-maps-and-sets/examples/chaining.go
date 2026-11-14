// A hash map with separate chaining that doubles its buckets when the load factor passes 0.75.
//
// It hashes with CRC-32, the checksum zlib computes, so every run, in every language, fills the
// same buckets.
package main

import (
	"fmt"
	"hash/crc32"
)

const maxLoad = 0.75

type entry struct {
	key   string
	value int
}

type chainedMap struct {
	buckets [][]entry
	size    int
	moved   int // entries copied by every resize so far
}

func newChainedMap() *chainedMap {
	return &chainedMap{buckets: make([][]entry, 4)}
}

func (m *chainedMap) bucketOf(key string) int {
	return int(crc32.ChecksumIEEE([]byte(key)) % uint32(len(m.buckets)))
}

func (m *chainedMap) put(key string, value int) {
	b := m.bucketOf(key)
	for i, stored := range m.buckets[b] {
		if stored.key == key { // a collision is fine: compare the keys themselves
			m.buckets[b][i].value = value
			return
		}
	}
	m.buckets[b] = append(m.buckets[b], entry{key, value})
	m.size++
	if float64(m.size)/float64(len(m.buckets)) > maxLoad {
		m.resize(2 * len(m.buckets))
	}
}

// get returns the key's value, and whether the map holds the key.
func (m *chainedMap) get(key string) (int, bool) {
	for _, stored := range m.buckets[m.bucketOf(key)] {
		if stored.key == key {
			return stored.value, true
		}
	}
	return 0, false
}

func (m *chainedMap) resize(count int) {
	old := m.buckets
	m.buckets = make([][]entry, count)
	for _, chain := range old {
		for _, stored := range chain {
			b := m.bucketOf(stored.key)
			m.buckets[b] = append(m.buckets[b], stored)
			m.moved++
		}
	}
}

func main() {
	ages := newChainedMap()
	for i, name := range []string{"ada", "bo", "cy", "di"} {
		ages.put(name, 30+i)
		fmt.Printf("put %s: %d entries in %d buckets\n", name, ages.size, len(ages.buckets))
	}
	cy, hasCy := ages.get("cy")
	zed, hasZed := ages.get("zed")
	fmt.Printf("get('cy') = %d, %t | get('zed') = %d, %t\n", cy, hasCy, zed, hasZed)

	for _, count := range []int{1_000, 100_000} {
		table := newChainedMap()
		for number := range count {
			table.put(fmt.Sprintf("key%d", number), number)
		}
		longest := 0
		for _, chain := range table.buckets {
			longest = max(longest, len(chain))
		}
		fmt.Printf("%7d puts: %6d buckets, %.2f moves per put, longest chain %d\n",
			count, len(table.buckets), float64(table.moved)/float64(count), longest)
	}
}
