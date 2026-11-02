// Package inbox declares the entry type: cstudy grades Inbox, built with NewInbox, on the virtual
// clock.
//
// Receive and Sleep wait on the time package, which the grading binary's bubble makes virtual.
// Hold, Jam and Leave exist for the runner's conformance: Hold waits on a channel nobody sends to
// (a deadlock), Jam waits on a mutex it holds (a wait the clock cannot see), and Leave starts a
// goroutine that never ends.
package inbox

import (
	"sync"
	"time"
)

// Inbox hands messages to receivers that wait for them.
type Inbox struct {
	messages  chan string
	published int
	never     chan string
	mu        sync.Mutex
}

// NewInbox returns an empty inbox.
func NewInbox() *Inbox {
	return &Inbox{messages: make(chan string, 64), never: make(chan string)}
}

// Publish hands body to a waiting or later Receive and returns how many messages were published.
func (b *Inbox) Publish(body string) int {
	b.messages <- body
	b.published++
	return b.published
}

// Receive returns the next message, or "" once waitMs milliseconds passed without one.
func (b *Inbox) Receive(waitMs int) string {
	timer := time.NewTimer(time.Duration(waitMs) * time.Millisecond)
	defer timer.Stop()
	select {
	case body := <-b.messages:
		return body
	case <-timer.C:
		return ""
	}
}

// Sleep waits ms milliseconds and returns how long it waited, as the time package measures it.
func (b *Inbox) Sleep(ms int) int64 {
	start := time.Now()
	time.Sleep(time.Duration(ms) * time.Millisecond)
	return time.Since(start).Milliseconds()
}

// Hold waits for a message on a channel nobody sends to.
func (b *Inbox) Hold() string {
	return <-b.never
}

// Jam locks a mutex it already holds.
func (b *Inbox) Jam() string {
	b.mu.Lock()
	b.mu.Lock()
	return ""
}

// Leave starts a goroutine that waits for good, and returns.
func (b *Inbox) Leave() {
	go func() { <-b.never }()
}
