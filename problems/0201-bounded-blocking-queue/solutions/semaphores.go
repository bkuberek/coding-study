package bounded_blocking_queue

import "sync"

// BoundedBlockingQueue counts with buffered channels, Go's counting semaphores: free holds one
// token per empty slot and stored one per value, and receiving a token blocks while there is
// none. The mutex guards only the ring buffer.
type BoundedBlockingQueue struct {
	free   chan struct{}
	stored chan struct{}
	mu     sync.Mutex
	values []int
	head   int
	count  int
}

func NewBoundedBlockingQueue(capacity int) *BoundedBlockingQueue {
	q := &BoundedBlockingQueue{
		free:   make(chan struct{}, capacity),
		stored: make(chan struct{}, capacity),
		values: make([]int, capacity),
	}
	for range capacity {
		q.free <- struct{}{}
	}
	return q
}

func (q *BoundedBlockingQueue) Put(value int) {
	<-q.free
	q.mu.Lock()
	q.values[(q.head+q.count)%len(q.values)] = value
	q.count++
	q.mu.Unlock()
	q.stored <- struct{}{}
}

func (q *BoundedBlockingQueue) Take() int {
	<-q.stored
	q.mu.Lock()
	value := q.values[q.head]
	q.head = (q.head + 1) % len(q.values)
	q.count--
	q.mu.Unlock()
	q.free <- struct{}{}
	return value
}

func (q *BoundedBlockingQueue) Size() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return q.count
}
