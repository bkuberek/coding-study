package randomized_set

import "math/rand/v2"

type RandomizedSet struct {
	values  []int
	indexOf map[int]int
}

func NewRandomizedSet() *RandomizedSet {
	return &RandomizedSet{indexOf: make(map[int]int)}
}

func (s *RandomizedSet) Insert(value int) bool {
	if _, ok := s.indexOf[value]; ok {
		return false
	}
	s.indexOf[value] = len(s.values)
	s.values = append(s.values, value)
	return true
}

func (s *RandomizedSet) Remove(value int) bool {
	index, ok := s.indexOf[value]
	if !ok {
		return false
	}
	delete(s.indexOf, value)
	last := s.values[len(s.values)-1]
	s.values = s.values[:len(s.values)-1]
	if index < len(s.values) {
		// Fill the gap with the former last value and record its new position.
		s.values[index] = last
		s.indexOf[last] = index
	}
	return true
}

func (s *RandomizedSet) GetRandom() int {
	return s.values[rand.IntN(len(s.values))]
}
