package read_write_lock

import "sync"

// ReadWriteLock keeps its counters under one mutex. Readers wait on readable while a writer
// holds or waits for the lock, so a steady flow of readers cannot starve the writers; writers
// wait on writable while anyone holds it.
type ReadWriteLock struct {
	mu             sync.Mutex
	readable       *sync.Cond
	writable       *sync.Cond
	readers        int
	writing        bool
	waitingWriters int
}

func NewReadWriteLock() *ReadWriteLock {
	l := &ReadWriteLock{}
	l.readable = sync.NewCond(&l.mu)
	l.writable = sync.NewCond(&l.mu)
	return l
}

func (l *ReadWriteLock) AcquireRead() {
	l.mu.Lock()
	defer l.mu.Unlock()
	for l.writing || l.waitingWriters > 0 {
		l.readable.Wait()
	}
	l.readers++
}

func (l *ReadWriteLock) ReleaseRead() {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.readers--
	if l.readers == 0 {
		l.writable.Signal()
	}
}

func (l *ReadWriteLock) AcquireWrite() {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.waitingWriters++
	for l.writing || l.readers > 0 {
		l.writable.Wait()
	}
	l.waitingWriters--
	l.writing = true
}

func (l *ReadWriteLock) ReleaseWrite() {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.writing = false
	if l.waitingWriters > 0 {
		l.writable.Signal()
	} else {
		l.readable.Broadcast()
	}
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
