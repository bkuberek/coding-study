package concurrency_limiter

// ConcurrencyLimiter is a buffered channel used as a semaphore, Go's standard counting
// semaphore: each holder has a token in the channel. Senders blocked on a full channel queue
// first come, first served, and a receive moves the oldest one's token in at once, so a
// released permit goes to the longest waiter.
type ConcurrencyLimiter struct {
	held chan struct{}
}

func NewConcurrencyLimiter(limit int) *ConcurrencyLimiter {
	return &ConcurrencyLimiter{held: make(chan struct{}, limit)}
}

func (l *ConcurrencyLimiter) Acquire() {
	l.held <- struct{}{}
}

func (l *ConcurrencyLimiter) TryAcquire() bool {
	select {
	case l.held <- struct{}{}:
		return true
	default:
		return false
	}
}

func (l *ConcurrencyLimiter) Release() {
	<-l.held
}

func (l *ConcurrencyLimiter) Available() int {
	return cap(l.held) - len(l.held)
}
