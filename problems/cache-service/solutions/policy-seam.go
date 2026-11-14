package cache_service

import (
	"container/heap"
	"container/list"
)

// orderedKeys is an insertion-ordered set of keys with O(1) move-to-back and removal. Go has no
// ordered map, so a map points into a linked list.
type orderedKeys struct {
	order    *list.List
	elements map[string]*list.Element
}

func newOrderedKeys() *orderedKeys {
	return &orderedKeys{order: list.New(), elements: make(map[string]*list.Element)}
}

func (o *orderedKeys) pushBack(key string) {
	o.elements[key] = o.order.PushBack(key)
}

func (o *orderedKeys) moveToBack(key string) {
	o.order.MoveToBack(o.elements[key])
}

func (o *orderedKeys) remove(key string) {
	o.order.Remove(o.elements[key])
	delete(o.elements, key)
}

func (o *orderedKeys) front() string {
	return o.order.Front().Value.(string)
}

func (o *orderedKeys) empty() bool {
	return o.order.Len() == 0
}

// evictionPolicy tracks the live keys and names the one to evict when the cache is full.
type evictionPolicy interface {
	admit(key string)
	touch(key string)
	forget(key string)
	victim() string
}

type lruPolicy struct {
	order *orderedKeys // least recently used first
}

func newLruPolicy() *lruPolicy {
	return &lruPolicy{order: newOrderedKeys()}
}

func (p *lruPolicy) admit(key string)  { p.order.pushBack(key) }
func (p *lruPolicy) touch(key string)  { p.order.moveToBack(key) }
func (p *lruPolicy) forget(key string) { p.order.remove(key) }
func (p *lruPolicy) victim() string    { return p.order.front() }

// fifoPolicy is the LRU order without the move: using a key does not change its place, so the
// oldest insertion goes first.
type fifoPolicy struct {
	*lruPolicy
}

func (p fifoPolicy) touch(key string) {}

// lfuPolicy evicts the least frequently used key; among equal counts, the least recently used.
type lfuPolicy struct {
	counts  map[string]int
	buckets map[int]*orderedKeys
	lowest  int // never above the lowest count in use
}

func newLfuPolicy() *lfuPolicy {
	return &lfuPolicy{counts: make(map[string]int), buckets: make(map[int]*orderedKeys), lowest: 1}
}

func (p *lfuPolicy) admit(key string) {
	p.place(key, 1)
	p.lowest = 1
}

func (p *lfuPolicy) touch(key string) {
	count := p.counts[key]
	p.unplace(key, count)
	p.place(key, count+1)
}

func (p *lfuPolicy) forget(key string) {
	p.unplace(key, p.counts[key])
	delete(p.counts, key)
}

func (p *lfuPolicy) victim() string {
	for {
		if bucket := p.buckets[p.lowest]; bucket != nil && !bucket.empty() {
			return bucket.front()
		}
		p.lowest++
	}
}

func (p *lfuPolicy) place(key string, count int) {
	p.counts[key] = count
	bucket, ok := p.buckets[count]
	if !ok {
		bucket = newOrderedKeys()
		p.buckets[count] = bucket
	}
	bucket.pushBack(key)
}

func (p *lfuPolicy) unplace(key string, count int) {
	p.buckets[count].remove(key)
}

func newPolicy(name string) evictionPolicy {
	switch name {
	case "LRU":
		return newLruPolicy()
	case "LFU":
		return newLfuPolicy()
	case "FIFO":
		return fifoPolicy{newLruPolicy()}
	}
	panic("unknown eviction policy " + name)
}

type entry struct {
	value     string
	expiresAt int64
	expires   bool
}

func (e *entry) expired(now int64) bool {
	return e.expires && now >= e.expiresAt
}

type expiry struct {
	expiresAt int64
	key       string
}

// expiryHeap is a min-heap of expiries; stale pairs are skipped when they surface.
type expiryHeap []expiry

func (h expiryHeap) Len() int { return len(h) }
func (h expiryHeap) Less(i, j int) bool {
	if h[i].expiresAt != h[j].expiresAt {
		return h[i].expiresAt < h[j].expiresAt
	}
	return h[i].key < h[j].key
}
func (h expiryHeap) Swap(i, j int) { h[i], h[j] = h[j], h[i] }
func (h *expiryHeap) Push(x any)   { *h = append(*h, x.(expiry)) }
func (h *expiryHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

type CacheService struct {
	capacity                             int
	policy                               evictionPolicy
	entries                              map[string]*entry
	expiries                             expiryHeap
	hits, misses, evictions, expirations int
}

func NewCacheService(capacity int, policy string) *CacheService {
	return &CacheService{capacity: capacity, policy: newPolicy(policy), entries: make(map[string]*entry)}
}

func (c *CacheService) Put(timestamp int64, key string, value string, ttl int64) {
	expires := ttl > 0
	expiresAt := timestamp + ttl
	if e := c.live(timestamp, key); e != nil {
		e.value, e.expiresAt, e.expires = value, expiresAt, expires
		c.policy.touch(key)
	} else {
		c.makeRoom(timestamp)
		c.entries[key] = &entry{value: value, expiresAt: expiresAt, expires: expires}
		c.policy.admit(key)
	}
	if expires {
		heap.Push(&c.expiries, expiry{expiresAt, key})
	}
}

func (c *CacheService) Get(timestamp int64, key string) string {
	e := c.live(timestamp, key)
	if e == nil {
		c.misses++
		return ""
	}
	c.hits++
	c.policy.touch(key)
	return e.value
}

func (c *CacheService) Remove(timestamp int64, key string) bool {
	if c.live(timestamp, key) == nil {
		return false
	}
	c.drop(key)
	return true
}

func (c *CacheService) Size(timestamp int64) int {
	c.purgeExpired(timestamp)
	return len(c.entries)
}

func (c *CacheService) Stats() []int {
	return []int{c.hits, c.misses, c.evictions, c.expirations}
}

// live returns the entry for key, expiring it first when its time is up.
func (c *CacheService) live(now int64, key string) *entry {
	e := c.entries[key]
	if e != nil && e.expired(now) {
		c.expire(key)
		return nil
	}
	return e
}

func (c *CacheService) makeRoom(now int64) {
	if len(c.entries) < c.capacity {
		return
	}
	c.purgeExpired(now)
	if len(c.entries) >= c.capacity {
		c.drop(c.policy.victim())
		c.evictions++
	}
}

func (c *CacheService) purgeExpired(now int64) {
	for len(c.expiries) > 0 && c.expiries[0].expiresAt <= now {
		due := heap.Pop(&c.expiries).(expiry)
		if e := c.entries[due.key]; e != nil && e.expires && e.expiresAt == due.expiresAt {
			c.expire(due.key)
		}
	}
}

func (c *CacheService) expire(key string) {
	c.drop(key)
	c.expirations++
}

func (c *CacheService) drop(key string) {
	delete(c.entries, key)
	c.policy.forget(key)
}
