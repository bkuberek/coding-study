// Package probe declares the entry type: cstudy grades Probe, built with NewProbe.
package probe

// Probe answers pings.
type Probe struct{}

// NewProbe returns a probe.
func NewProbe() *Probe {
	return &Probe{}
}

// Ping answers pong.
func (p *Probe) Ping() string {
	panic("not implemented")
}
