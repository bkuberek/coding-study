package conformance_stress_sections

type StressMutex struct{}

func NewStressMutex() *StressMutex {
	return &StressMutex{}
}

func (m *StressMutex) Lock() {}

func (m *StressMutex) Unlock() {}
