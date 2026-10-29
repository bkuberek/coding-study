package read_write_lock

import (
	"runtime"
	"sync"
)

type ReadWriteLock struct {
	writers sync.Mutex
	writing bool
	readers int
}

func NewReadWriteLock() *ReadWriteLock {
	return &ReadWriteLock{}
}

func (l *ReadWriteLock) AcquireRead() {
	for l.writing {
		runtime.Gosched()
	}
	l.readers++
}

func (l *ReadWriteLock) ReleaseRead() {
	l.readers--
}

func (l *ReadWriteLock) AcquireWrite() {
	l.writers.Lock()
	for l.readers > 0 {
		runtime.Gosched()
	}
	l.writing = true
}

func (l *ReadWriteLock) ReleaseWrite() {
	l.writing = false
	l.writers.Unlock()
}

func (l *ReadWriteLock) TryAcquireRead() bool {
	if l.writing {
		return false
	}
	l.readers++
	return true
}

func (l *ReadWriteLock) TryAcquireWrite() bool {
	if !l.writers.TryLock() {
		return false
	}
	if l.readers > 0 {
		l.writers.Unlock()
		return false
	}
	l.writing = true
	return true
}
