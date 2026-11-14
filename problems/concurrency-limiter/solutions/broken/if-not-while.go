package concurrency_limiter

import "sync"

type ConcurrencyLimiter struct {
	mu       sync.Mutex
	released *sync.Cond
	permits  int
}

func NewConcurrencyLimiter(limit int) *ConcurrencyLimiter {
	l := &ConcurrencyLimiter{permits: limit}
	l.released = sync.NewCond(&l.mu)
	return l
}

func (l *ConcurrencyLimiter) Acquire() {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.permits == 0 {
		l.released.Wait()
	}
	l.permits--
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
	l.permits++
	l.released.Broadcast()
}

func (l *ConcurrencyLimiter) Available() int {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.permits
}
