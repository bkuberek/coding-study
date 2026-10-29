// Bounded Blocking Queue. Statement: .statements/bounded-blocking-queue.md. Run: cstudy test bounded-blocking-queue
// Concurrency: threads

package bounded_blocking_queue

type BoundedBlockingQueue struct{}

func NewBoundedBlockingQueue(capacity int) *BoundedBlockingQueue {
	return &BoundedBlockingQueue{}
}

func (q *BoundedBlockingQueue) Put(value int) {
	panic("not implemented")
}

func (q *BoundedBlockingQueue) Take() int {
	panic("not implemented")
}

func (q *BoundedBlockingQueue) Size() int {
	panic("not implemented")
}
