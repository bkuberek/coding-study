use std::sync::{Condvar, Mutex};

struct State {
    readers: u32,
    writing: bool,
    waiting_writers: u32,
}

/// The counters live under one mutex. Readers wait on `readable` while a writer holds or waits
/// for the lock, so a steady flow of readers cannot starve the writers; writers wait on
/// `writable` while anyone holds it. A guard cannot outlive the method that took it, so the
/// lock's state is these counters, not a held `MutexGuard`.
pub struct ReadWriteLock {
    state: Mutex<State>,
    readable: Condvar,
    writable: Condvar,
}

impl ReadWriteLock {
    pub fn new() -> Self {
        ReadWriteLock {
            state: Mutex::new(State {
                readers: 0,
                writing: false,
                waiting_writers: 0,
            }),
            readable: Condvar::new(),
            writable: Condvar::new(),
        }
    }

    pub fn acquire_read(&self) {
        let mut state = self.state.lock().unwrap();
        while state.writing || state.waiting_writers > 0 {
            state = self.readable.wait(state).unwrap();
        }
        state.readers += 1;
    }

    pub fn release_read(&self) {
        let mut state = self.state.lock().unwrap();
        state.readers -= 1;
        if state.readers == 0 {
            self.writable.notify_one();
        }
    }

    pub fn acquire_write(&self) {
        let mut state = self.state.lock().unwrap();
        state.waiting_writers += 1;
        while state.writing || state.readers > 0 {
            state = self.writable.wait(state).unwrap();
        }
        state.waiting_writers -= 1;
        state.writing = true;
    }

    pub fn release_write(&self) {
        let mut state = self.state.lock().unwrap();
        state.writing = false;
        if state.waiting_writers > 0 {
            self.writable.notify_one();
        } else {
            self.readable.notify_all();
        }
    }

    pub fn try_acquire_read(&self) -> bool {
        let mut state = self.state.lock().unwrap();
        if state.writing || state.waiting_writers > 0 {
            return false;
        }
        state.readers += 1;
        true
    }

    pub fn try_acquire_write(&self) -> bool {
        let mut state = self.state.lock().unwrap();
        if state.writing || state.readers > 0 {
            return false;
        }
        state.writing = true;
        true
    }
}
