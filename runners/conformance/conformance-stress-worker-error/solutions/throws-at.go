package conformance_stress_worker_error

import "fmt"

type StressFailer struct{}

func NewStressFailer() *StressFailer {
	return &StressFailer{}
}

func (f *StressFailer) Step(index int) int {
	if index == 100 {
		panic(fmt.Sprintf("failed at %d", index))
	}
	return index
}
