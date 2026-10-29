package lru_cache

type node struct {
	key, value int
	prev, next *node
}

type LRUCache struct {
	capacity int
	nodes    map[int]*node
	// Sentinels: head.next is the least recently used node, tail.prev the most recent.
	head, tail *node
}

func NewLRUCache(capacity int) *LRUCache {
	head, tail := &node{}, &node{}
	head.next, tail.prev = tail, head
	return &LRUCache{capacity: capacity, nodes: make(map[int]*node, capacity), head: head, tail: tail}
}

func (c *LRUCache) Get(key int) int {
	n, ok := c.nodes[key]
	if !ok {
		return -1
	}
	c.unlink(n)
	c.append(n)
	return n.value
}

func (c *LRUCache) Put(key int, value int) {
	if n, ok := c.nodes[key]; ok {
		n.value = value
		c.unlink(n)
		c.append(n)
		return
	}
	if len(c.nodes) == c.capacity {
		oldest := c.head.next
		c.unlink(oldest)
		delete(c.nodes, oldest.key)
	}
	n := &node{key: key, value: value}
	c.nodes[key] = n
	c.append(n)
}

func (c *LRUCache) unlink(n *node) {
	n.prev.next = n.next
	n.next.prev = n.prev
}

func (c *LRUCache) append(n *node) {
	last := c.tail.prev
	last.next, n.prev = n, last
	n.next, c.tail.prev = c.tail, n
}
