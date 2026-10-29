package thread_safe_lru_cache

import "sync"

type node struct {
	key, value int
	prev, next *node
}

type LRUCache struct {
	capacity int
	nodes    sync.Map
	size     int
	head     *node
	tail     *node
}

func NewLRUCache(capacity int) *LRUCache {
	head, tail := &node{}, &node{}
	head.next, tail.prev = tail, head
	return &LRUCache{capacity: capacity, head: head, tail: tail}
}

func (c *LRUCache) Get(key int) int {
	found, ok := c.nodes.Load(key)
	if !ok {
		return -1
	}
	n := found.(*node)
	c.unlink(n)
	c.pushBack(n)
	return n.value
}

func (c *LRUCache) Put(key int, value int) {
	if found, ok := c.nodes.Load(key); ok {
		n := found.(*node)
		n.value = value
		c.unlink(n)
		c.pushBack(n)
		return
	}
	if c.size == c.capacity {
		oldest := c.head.next
		c.unlink(oldest)
		c.nodes.Delete(oldest.key)
		c.size--
	}
	n := &node{key: key, value: value}
	c.nodes.Store(key, n)
	c.size++
	c.pushBack(n)
}

func (c *LRUCache) Size() int {
	return c.size
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
