package lru_cache

import "container/list"

type entry struct {
	key, value int
}

// LRUCache keeps entries in a container/list, least recently used at the front; Go has no
// insertion-ordered map, so the map points into the list.
type LRUCache struct {
	capacity int
	order    *list.List
	elements map[int]*list.Element
}

func NewLRUCache(capacity int) *LRUCache {
	return &LRUCache{capacity: capacity, order: list.New(), elements: make(map[int]*list.Element, capacity)}
}

func (c *LRUCache) Get(key int) int {
	element, ok := c.elements[key]
	if !ok {
		return -1
	}
	c.order.MoveToBack(element)
	return element.Value.(entry).value
}

func (c *LRUCache) Put(key int, value int) {
	if element, ok := c.elements[key]; ok {
		element.Value = entry{key, value}
		c.order.MoveToBack(element)
		return
	}
	if c.order.Len() == c.capacity {
		oldest := c.order.Front()
		c.order.Remove(oldest)
		delete(c.elements, oldest.Value.(entry).key)
	}
	c.elements[key] = c.order.PushBack(entry{key, value})
}
