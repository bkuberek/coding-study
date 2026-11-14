// Open addressing with linear probing: a key that finds its home slot taken tries the next one.
//
// Keys are small integers hashed as `key % 8`, so that the collisions are easy to follow.
package main

import "fmt"

const slotCount = 8

// deleted is a tombstone: the slot is free to reuse, but a search goes on past it.
const deleted = "<deleted>"

// probingSet holds each key in a slot; nil is an empty slot.
type probingSet struct {
	slots [slotCount]any
}

// probe gives the slots to try for key: its home slot, then the next ones, wrapping around.
func probe(key int) []int {
	home := key % slotCount
	order := make([]int, slotCount)
	for step := range slotCount {
		order[step] = (home + step) % slotCount
	}
	return order
}

func (s *probingSet) add(key int) []int {
	var tried []int
	reusable := -1
	for _, slot := range probe(key) {
		tried = append(tried, slot)
		if s.slots[slot] == key {
			return tried
		}
		if s.slots[slot] == deleted && reusable == -1 {
			reusable = slot
		}
		if s.slots[slot] == nil {
			if reusable == -1 {
				reusable = slot
			}
			s.slots[reusable] = key
			return tried
		}
	}
	panic("full: a real table resizes long before this")
}

// contains reports whether key is in the set, and the slots it tried.
func (s *probingSet) contains(key int) (bool, []int) {
	var tried []int
	for _, slot := range probe(key) {
		tried = append(tried, slot)
		if s.slots[slot] == nil {
			return false, tried
		}
		if s.slots[slot] == key {
			return true, tried
		}
	}
	return false, tried
}

func (s *probingSet) remove(key int, tombstone bool) {
	for _, slot := range probe(key) {
		if s.slots[slot] == key {
			if tombstone {
				s.slots[slot] = deleted
			} else {
				s.slots[slot] = nil
			}
			return
		}
	}
}

func main() {
	var table probingSet
	for _, key := range []int{3, 11, 19, 6} {
		fmt.Printf("add %2d: home %d, tried slots %v\n", key, key%slotCount, table.add(key))
	}
	fmt.Println("slots:", table.slots)

	table.remove(11, true)
	fmt.Println("remove 11 with a tombstone:", table.slots)
	found, tried := table.contains(19)
	fmt.Println("contains 19?", found, tried)

	var broken probingSet
	for _, key := range []int{3, 11, 19} {
		broken.add(key)
	}
	broken.remove(11, false)
	found, tried = broken.contains(19)
	fmt.Println("remove 11 by emptying its slot, contains 19?", found, tried)
}
