package read_write_lock

import "sync"

type ReadWriteLock struct {
	mu             sync.Mutex
	changed        *sync.Cond
	readers        int
	writing        bool
	waitingWriters int
}

func NewReadWriteLock() *ReadWriteLock {
	l := &ReadWriteLock{}
	l.changed = sync.NewCond(&l.mu)
	return l
}

func (l *ReadWriteLock) AcquireRead() {
	l.mu.Lock()
	defer l.mu.Unlock()
	for l.writing || l.waitingWriters > 0 {
		l.changed.Wait()
	}
	l.readers++
}

func (l *ReadWriteLock) ReleaseRead() {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.readers--
	if l.readers == 0 {
		l.changed.Broadcast()
	}
}

func (l *ReadWriteLock) AcquireWrite() {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.waitingWriters++
	if l.writing || l.readers > 0 {
		l.changed.Wait()
	}
	l.waitingWriters--
	l.writing = true
}

func (l *ReadWriteLock) ReleaseWrite() {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.writing = false
	l.changed.Broadcast()
}

func (l *ReadWriteLock) TryAcquireRead() bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.writing || l.waitingWriters > 0 {
		return false
	}
	l.readers++
	return true
}

func (l *ReadWriteLock) TryAcquireWrite() bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.writing || l.readers > 0 {
		return false
	}
	l.writing = true
	return true
}
