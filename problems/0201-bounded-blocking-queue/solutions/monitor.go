package bounded_blocking_queue

import "sync"

// BoundedBlockingQueue keeps its values in a ring buffer under one mutex. Producers wait on
// notFull and consumers on notEmpty, two conditions on the same mutex.
type BoundedBlockingQueue struct {
	mu       sync.Mutex
	notFull  *sync.Cond
	notEmpty *sync.Cond
	values   []int
	head     int
	count    int
}

func NewBoundedBlockingQueue(capacity int) *BoundedBlockingQueue {
	q := &BoundedBlockingQueue{values: make([]int, capacity)}
	q.notFull = sync.NewCond(&q.mu)
	q.notEmpty = sync.NewCond(&q.mu)
	return q
}

func (q *BoundedBlockingQueue) Put(value int) {
	q.mu.Lock()
	defer q.mu.Unlock()
	for q.count == len(q.values) {
		q.notFull.Wait()
	}
	q.values[(q.head+q.count)%len(q.values)] = value
	q.count++
	q.notEmpty.Signal()
}

func (q *BoundedBlockingQueue) Take() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	for q.count == 0 {
		q.notEmpty.Wait()
	}
	value := q.values[q.head]
	q.head = (q.head + 1) % len(q.values)
	q.count--
	q.notFull.Signal()
	return value
}

func (q *BoundedBlockingQueue) Size() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return q.count
}
