package bounded_blocking_queue

import (
	"runtime"
	"sync/atomic"
)

type BoundedBlockingQueue struct {
	values []int
	head   atomic.Int64
	tail   atomic.Int64
}

func NewBoundedBlockingQueue(capacity int) *BoundedBlockingQueue {
	return &BoundedBlockingQueue{values: make([]int, capacity)}
}

func (q *BoundedBlockingQueue) Put(value int) {
	for q.tail.Load()-q.head.Load() >= int64(len(q.values)) {
		runtime.Gosched()
	}
	slot := q.tail.Add(1) - 1
	q.values[slot%int64(len(q.values))] = value
}

func (q *BoundedBlockingQueue) Take() int {
	for q.tail.Load() == q.head.Load() {
		runtime.Gosched()
	}
	slot := q.head.Add(1) - 1
	return q.values[slot%int64(len(q.values))]
}

func (q *BoundedBlockingQueue) Size() int {
	return int(q.tail.Load() - q.head.Load())
}
