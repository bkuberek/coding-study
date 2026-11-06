// LRU Cache.
//
// Build a key-value cache with a fixed number of slots that discards
// the entry unused for the longest time when it is full.
//
// Statement: .statements/lru-cache.md
// Run: cstudy test lru-cache

package lru_cache

type LRUCache struct{}

func NewLRUCache(capacity int) *LRUCache {
	return &LRUCache{}
}

func (c *LRUCache) Get(key int) int {
	panic("not implemented")
}

func (c *LRUCache) Put(key int, value int) {
	panic("not implemented")
}
