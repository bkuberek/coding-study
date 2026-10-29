package token_bucket_limiter

import "sync"

// TokenBucket refills lazily: each call first adds the tokens earned since the last refill,
// then reads or takes. One mutex makes the refill and the take a single step.
type TokenBucket struct {
	mu              sync.Mutex
	capacity        int64
	refillPerSecond int64
	stored          int64
	lastRefill      int64
}

func NewTokenBucket(capacity int64, refillPerSecond int64) *TokenBucket {
	return &TokenBucket{capacity: capacity, refillPerSecond: refillPerSecond, stored: capacity}
}

func (b *TokenBucket) TryAcquire(timestamp int64, tokens int64) bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.refill(timestamp)
	if b.stored < tokens {
		return false
	}
	b.stored -= tokens
	return true
}

func (b *TokenBucket) Available(timestamp int64) int64 {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.refill(timestamp)
	return b.stored
}

func (b *TokenBucket) refill(timestamp int64) {
	if timestamp <= b.lastRefill {
		return
	}
	b.stored = min(b.capacity, b.stored+(timestamp-b.lastRefill)*b.refillPerSecond)
	b.lastRefill = timestamp
}
