package lru_cache

type entry struct {
	key, value int
}

type LRUCache struct {
	capacity int
	// Ordered from least to most recently used.
	entries []entry
}

func NewLRUCache(capacity int) *LRUCache {
	return &LRUCache{capacity: capacity}
}

func (c *LRUCache) Get(key int) int {
	index := c.indexOf(key)
	if index < 0 {
		return -1
	}
	found := c.entries[index]
	c.entries = append(c.entries[:index], c.entries[index+1:]...)
	c.entries = append(c.entries, found)
	return found.value
}

func (c *LRUCache) Put(key int, value int) {
	if index := c.indexOf(key); index >= 0 {
		c.entries = append(c.entries[:index], c.entries[index+1:]...)
	} else if len(c.entries) == c.capacity {
		c.entries = c.entries[1:]
	}
	c.entries = append(c.entries, entry{key, value})
}

func (c *LRUCache) indexOf(key int) int {
	for i, e := range c.entries {
		if e.key == key {
			return i
		}
	}
	return -1
}
