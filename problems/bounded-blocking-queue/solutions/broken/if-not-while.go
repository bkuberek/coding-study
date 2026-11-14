package bounded_blocking_queue

import "sync"

type BoundedBlockingQueue struct {
	mu       sync.Mutex
	changed  *sync.Cond
	capacity int
	values   []int
}

func NewBoundedBlockingQueue(capacity int) *BoundedBlockingQueue {
	q := &BoundedBlockingQueue{capacity: capacity}
	q.changed = sync.NewCond(&q.mu)
	return q
}

func (q *BoundedBlockingQueue) Put(value int) {
	q.mu.Lock()
	defer q.mu.Unlock()
	if len(q.values) >= q.capacity {
		q.changed.Wait()
	}
	q.values = append(q.values, value)
	q.changed.Broadcast()
}

func (q *BoundedBlockingQueue) Take() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	if len(q.values) == 0 {
		q.changed.Wait()
	}
	value := q.values[0]
	q.values = q.values[1:]
	q.changed.Broadcast()
	return value
}

func (q *BoundedBlockingQueue) Size() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return len(q.values)
}
