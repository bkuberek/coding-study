package conformance_stress_stall

type StressGate struct {
	open chan struct{}
}

func NewStressGate() *StressGate {
	return &StressGate{open: make(chan struct{})}
}

func (g *StressGate) Enter() {
	<-g.open
}
