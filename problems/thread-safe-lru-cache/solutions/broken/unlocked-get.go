package thread_safe_lru_cache

import "sync"

type node struct {
	key, value int
	prev, next *node
}

type LRUCache struct {
	mu         sync.RWMutex
	capacity   int
	nodes      map[int]*node
	head, tail *node
}

func NewLRUCache(capacity int) *LRUCache {
	head, tail := &node{}, &node{}
	head.next, tail.prev = tail, head
	return &LRUCache{capacity: capacity, nodes: make(map[int]*node, capacity), head: head, tail: tail}
}

func (c *LRUCache) Get(key int) int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	n, ok := c.nodes[key]
	if !ok {
		return -1
	}
	c.unlink(n)
	c.pushBack(n)
	return n.value
}

func (c *LRUCache) Put(key int, value int) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if n, ok := c.nodes[key]; ok {
		n.value = value
		c.unlink(n)
		c.pushBack(n)
		return
	}
	if len(c.nodes) == c.capacity {
		oldest := c.head.next
		c.unlink(oldest)
		delete(c.nodes, oldest.key)
	}
	n := &node{key: key, value: value}
	c.nodes[key] = n
	c.pushBack(n)
}

func (c *LRUCache) Size() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return len(c.nodes)
}

func (c *LRUCache) unlink(n *node) {
	n.prev.next = n.next
	n.next.prev = n.prev
}

func (c *LRUCache) pushBack(n *node) {
	last := c.tail.prev
	last.next, n.prev = n, last
	n.next, c.tail.prev = c.tail, n
}
