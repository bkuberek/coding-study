package concurrency_limiter

import "sync"

// ConcurrencyLimiter queues waiting workers first come, first served, each with a channel of its
// own. A release with workers waiting hands its permit straight to the oldest one by closing
// that worker's channel, so a newcomer can never take the permit in between.
type ConcurrencyLimiter struct {
	mu      sync.Mutex
	permits int
	waiters []chan struct{}
}

func NewConcurrencyLimiter(limit int) *ConcurrencyLimiter {
	return &ConcurrencyLimiter{permits: limit}
}

func (l *ConcurrencyLimiter) Acquire() {
	l.mu.Lock()
	if l.permits > 0 {
		l.permits--
		l.mu.Unlock()
		return
	}
	granted := make(chan struct{})
	l.waiters = append(l.waiters, granted)
	l.mu.Unlock()
	<-granted
}

func (l *ConcurrencyLimiter) TryAcquire() bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.permits == 0 {
		return false
	}
	l.permits--
	return true
}

func (l *ConcurrencyLimiter) Release() {
	l.mu.Lock()
	defer l.mu.Unlock()
	if len(l.waiters) == 0 {
		l.permits++
		return
	}
	next := l.waiters[0]
	l.waiters = l.waiters[1:]
	close(next)
}

func (l *ConcurrencyLimiter) Available() int {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.permits
}
