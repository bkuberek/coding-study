package conformance_stress_leak

import (
	"sync"
	"time"
)

type StressLeak struct {
	spinning chan struct{}
	started  sync.Once
}

func NewStressLeak() *StressLeak {
	return &StressLeak{spinning: make(chan struct{})}
}

// Spin never returns: Go cannot stop a goroutine, so the runner must ask for a restart.
func (l *StressLeak) Spin() {
	l.started.Do(func() { close(l.spinning) })
	for {
		time.Sleep(time.Millisecond)
	}
}

// Fail waits until Spin runs: a run that failed before the spinner's first op would stop it
// there, and leave nothing running.
func (l *StressLeak) Fail() {
	<-l.spinning
	panic("leak")
}

func (l *StressLeak) Noop() {}
