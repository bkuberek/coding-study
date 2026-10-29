package conformance_stress_leak

import "time"

type StressLeak struct{}

func NewStressLeak() *StressLeak {
	return &StressLeak{}
}

// Spin never returns: Go cannot stop a goroutine, so the runner must ask for a restart.
func (l *StressLeak) Spin() {
	for {
		time.Sleep(time.Millisecond)
	}
}

func (l *StressLeak) Fail() {
	panic("leak")
}

func (l *StressLeak) Noop() {}
