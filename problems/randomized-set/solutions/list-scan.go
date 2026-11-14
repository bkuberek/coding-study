package randomized_set

import (
	"math/rand/v2"
	"slices"
)

type RandomizedSet struct {
	values []int
}

func NewRandomizedSet() *RandomizedSet {
	return &RandomizedSet{}
}

func (s *RandomizedSet) Insert(value int) bool {
	if slices.Contains(s.values, value) {
		return false
	}
	s.values = append(s.values, value)
	return true
}

func (s *RandomizedSet) Remove(value int) bool {
	index := slices.Index(s.values, value)
	if index < 0 {
		return false
	}
	// Order does not matter: move the last value into the gap instead of shifting.
	last := len(s.values) - 1
	s.values[index] = s.values[last]
	s.values = s.values[:last]
	return true
}

func (s *RandomizedSet) GetRandom() int {
	return s.values[rand.IntN(len(s.values))]
}
