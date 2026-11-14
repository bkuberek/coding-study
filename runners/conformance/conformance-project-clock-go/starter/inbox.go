// Package inbox declares the entry type: cstudy grades Inbox, built with NewInbox, on the virtual
// clock.
package inbox

// Inbox hands messages to receivers that wait for them.
type Inbox struct{}

// NewInbox returns an empty inbox.
func NewInbox() *Inbox {
	return &Inbox{}
}

// Publish hands body to a waiting or later Receive and returns how many messages were published.
func (b *Inbox) Publish(body string) int {
	panic("not implemented")
}

// Receive returns the next message, or "" once waitMs milliseconds passed without one.
func (b *Inbox) Receive(waitMs int) string {
	panic("not implemented")
}

// Sleep waits ms milliseconds and returns how long it waited.
func (b *Inbox) Sleep(ms int) int64 {
	panic("not implemented")
}

// Hold waits for a message that never comes.
func (b *Inbox) Hold() string {
	panic("not implemented")
}

// Jam locks a mutex twice.
func (b *Inbox) Jam() string {
	panic("not implemented")
}

// Leave starts a goroutine that never ends.
func (b *Inbox) Leave() {
	panic("not implemented")
}
