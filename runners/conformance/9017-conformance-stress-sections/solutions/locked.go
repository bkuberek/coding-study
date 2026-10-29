package conformance_stress_sections

import "sync"

type StressMutex struct {
	mu sync.Mutex
}

func NewStressMutex() *StressMutex {
	return &StressMutex{}
}

func (m *StressMutex) Lock() {
	m.mu.Lock()
}

func (m *StressMutex) Unlock() {
	m.mu.Unlock()
}
