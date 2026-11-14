package randomized_set

import "math/rand/v2"

type RandomizedSet struct {
	values map[int]struct{}
}

func NewRandomizedSet() *RandomizedSet {
	return &RandomizedSet{values: make(map[int]struct{})}
}

func (s *RandomizedSet) Insert(value int) bool {
	if _, ok := s.values[value]; ok {
		return false
	}
	s.values[value] = struct{}{}
	return true
}

func (s *RandomizedSet) Remove(value int) bool {
	if _, ok := s.values[value]; !ok {
		return false
	}
	delete(s.values, value)
	return true
}

func (s *RandomizedSet) GetRandom() int {
	// A map has no positions: walk its iteration order to a random rank, O(n).
	rank := rand.IntN(len(s.values))
	for value := range s.values {
		if rank == 0 {
			return value
		}
		rank--
	}
	panic("getRandom on an empty set")
}
