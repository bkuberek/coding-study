use std::sync::{Condvar, Mutex};

struct State {
    readers: u32,
    writing: bool,
    waiting_writers: u32,
}

pub struct ReadWriteLock {
    state: Mutex<State>,
    changed: Condvar,
}

impl ReadWriteLock {
    pub fn new() -> Self {
        ReadWriteLock {
            state: Mutex::new(State {
                readers: 0,
                writing: false,
                waiting_writers: 0,
            }),
            changed: Condvar::new(),
        }
    }

    pub fn acquire_read(&self) {
        let mut state = self.state.lock().unwrap();
        while state.writing || state.waiting_writers > 0 {
            state = self.changed.wait(state).unwrap();
        }
        state.readers += 1;
    }

    pub fn release_read(&self) {
        let mut state = self.state.lock().unwrap();
        state.readers -= 1;
        if state.readers == 0 {
            self.changed.notify_all();
        }
    }

    pub fn acquire_write(&self) {
        let mut state = self.state.lock().unwrap();
        state.waiting_writers += 1;
        if state.writing || state.readers > 0 {
            state = self.changed.wait(state).unwrap();
        }
        state.waiting_writers -= 1;
        state.writing = true;
    }

    pub fn release_write(&self) {
        let mut state = self.state.lock().unwrap();
        state.writing = false;
        self.changed.notify_all();
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
