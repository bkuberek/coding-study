use std::sync::atomic::{AtomicBool, AtomicI32, Ordering};
use std::thread;

pub struct ReadWriteLock {
    writer_held: AtomicBool,
    writing: AtomicBool,
    readers: AtomicI32,
}

impl ReadWriteLock {
    pub fn new() -> Self {
        ReadWriteLock {
            writer_held: AtomicBool::new(false),
            writing: AtomicBool::new(false),
            readers: AtomicI32::new(0),
        }
    }

    pub fn acquire_read(&self) {
        while self.writing.load(Ordering::SeqCst) {
            thread::yield_now();
        }
        self.add_reader(1);
    }

    pub fn release_read(&self) {
        self.add_reader(-1);
    }

    pub fn acquire_write(&self) {
        while !self.try_hold_writer() {
            thread::yield_now();
        }
        while self.readers.load(Ordering::SeqCst) > 0 {
            thread::yield_now();
        }
        self.writing.store(true, Ordering::SeqCst);
    }

    pub fn release_write(&self) {
        self.writing.store(false, Ordering::SeqCst);
        self.writer_held.store(false, Ordering::SeqCst);
    }

    pub fn try_acquire_read(&self) -> bool {
        if self.writing.load(Ordering::SeqCst) {
            return false;
        }
        self.add_reader(1);
        true
    }

    pub fn try_acquire_write(&self) -> bool {
        if !self.try_hold_writer() {
            return false;
        }
        if self.readers.load(Ordering::SeqCst) > 0 {
            self.writer_held.store(false, Ordering::SeqCst);
            return false;
        }
        self.writing.store(true, Ordering::SeqCst);
        true
    }

    fn add_reader(&self, change: i32) {
        let readers = self.readers.load(Ordering::SeqCst);
        self.readers.store(readers + change, Ordering::SeqCst);
    }

    fn try_hold_writer(&self) -> bool {
        self.writer_held
            .compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst)
            .is_ok()
    }
}
