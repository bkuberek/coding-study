//! The global allocator: the system allocator, plus peak tracking for bench memory calls and
//! retention for identity checks. Both apply to the calling thread only, which is the case
//! thread that runs user code.
//!
//! **Memory** (docs/specs/performance-analysis.md#measurement): during [`measure`], every
//! allocation and free adjusts a running total that starts at zero, and the highest total is the
//! call's `heap_peak`, the way `tracemalloc` measures Python. Outside it nothing is counted, so
//! timed calls pay one thread-local read per allocation.
//!
//! **Retention**: during [`retaining`], freed memory is not returned to the system, so a node
//! that user code drops cannot be reused at the same address by a node it creates. Identity
//! checks (`as: index`, `no_alias_with`) compare addresses taken before the call, and would
//! otherwise mistake a new node for an old one. Only checked calls retain; the leak is bounded by
//! what one call frees, in a process that ends with the request.

use std::alloc::{GlobalAlloc, Layout, System};
use std::cell::Cell;

pub struct Counting;

thread_local! {
    // Constant initializers without destructors: reading them never allocates.
    static TRACKING: Cell<bool> = const { Cell::new(false) };
    static CURRENT: Cell<isize> = const { Cell::new(0) };
    static PEAK: Cell<isize> = const { Cell::new(0) };
    static RETAINING: Cell<bool> = const { Cell::new(false) };
    /// Set by the harness around checked calls (test cases and bench check calls), never
    /// around timed samples, so a bench never accumulates retained memory.
    static RETENTION_ALLOWED: Cell<bool> = const { Cell::new(false) };
}

#[global_allocator]
static GLOBAL: Counting = Counting;

fn flag(cell: &'static std::thread::LocalKey<Cell<bool>>) -> bool {
    cell.try_with(Cell::get).unwrap_or(false)
}

fn set(cell: &'static std::thread::LocalKey<Cell<bool>>, value: bool) {
    let _ = cell.try_with(|state| state.set(value));
}

/// Adds `delta` bytes to the running total of a tracking thread.
fn count(delta: isize) {
    if !flag(&TRACKING) {
        return;
    }
    let now = CURRENT.with(|current| {
        current.set(current.get() + delta);
        current.get()
    });
    PEAK.with(|peak| peak.set(peak.get().max(now)));
}

// SAFETY: every method forwards to `System` with the caller's layout; retention only skips
// frees, and its realloc copies into a fresh block of the requested layout.
unsafe impl GlobalAlloc for Counting {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let block = System.alloc(layout);
        if !block.is_null() {
            count(layout.size() as isize);
        }
        block
    }

    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        let block = System.alloc_zeroed(layout);
        if !block.is_null() {
            count(layout.size() as isize);
        }
        block
    }

    unsafe fn dealloc(&self, block: *mut u8, layout: Layout) {
        count(-(layout.size() as isize));
        if !flag(&RETAINING) {
            System.dealloc(block, layout);
        }
    }

    unsafe fn realloc(&self, block: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        if flag(&RETAINING) {
            let new_layout = Layout::from_size_align_unchecked(new_size, layout.align());
            let moved = self.alloc(new_layout);
            if !moved.is_null() {
                std::ptr::copy_nonoverlapping(block, moved, layout.size().min(new_size));
                self.dealloc(block, layout);
            }
            return moved;
        }
        let moved = System.realloc(block, layout, new_size);
        if !moved.is_null() {
            count(new_size as isize - layout.size() as isize);
        }
        moved
    }
}

/// Turns a flag off again when dropped, also during a panic.
struct Reset(&'static std::thread::LocalKey<Cell<bool>>);

impl Drop for Reset {
    fn drop(&mut self) {
        set(self.0, false);
    }
}

/// Runs `call` and returns its result with the peak of the bytes it held at once on this thread,
/// memory it freed that existed before the call subtracted. A panic propagates after tracking
/// stops.
pub fn measure<R>(call: impl FnOnce() -> R) -> (R, u64) {
    CURRENT.with(|current| current.set(0));
    PEAK.with(|peak| peak.set(0));
    set(&TRACKING, true);
    let reset = Reset(&TRACKING);
    let result = call();
    drop(reset);
    (result, PEAK.with(Cell::get).max(0) as u64)
}

/// Runs `call` with frees retained when the harness allows it (see the module documentation).
/// The bridge wraps the calls whose result is checked by node identity.
pub fn retaining<R>(call: impl FnOnce() -> R) -> R {
    if !flag(&RETENTION_ALLOWED) {
        return call();
    }
    set(&RETAINING, true);
    let _reset = Reset(&RETAINING);
    call()
}

/// Runs `call` with retention allowed; a panic propagates after it is disallowed again.
pub(crate) fn checked<R>(call: impl FnOnce() -> R) -> R {
    set(&RETENTION_ALLOWED, true);
    let _reset = Reset(&RETENTION_ALLOWED);
    call()
}

#[cfg(test)]
mod tests {
    use super::{checked, measure, retaining};
    use std::hint::black_box;

    #[test]
    fn measures_the_peak_of_a_call() {
        let (_, bytes) = measure(|| {
            let first = black_box(vec![0_u8; 10_000]);
            drop(first);
            black_box(vec![0_u8; 4_000])
        });
        assert_eq!(bytes, 10_000);
    }

    #[test]
    fn freeing_older_memory_lowers_the_running_total() {
        let old = black_box(vec![0_u8; 50_000]);
        let (_, bytes) = measure(move || {
            drop(old);
            black_box(vec![0_u8; 20_000])
        });
        assert_eq!(bytes, 0);
    }

    #[test]
    fn retained_blocks_are_not_reused() {
        let (dropped, created) = checked(|| {
            retaining(|| {
                let first = black_box(Box::new(7_u64));
                let address = &*first as *const u64 as usize;
                drop(first);
                let second = black_box(Box::new(8_u64));
                (address, &*second as *const u64 as usize)
            })
        });
        assert_ne!(dropped, created);
    }

    #[test]
    fn retention_needs_a_checked_call() {
        let reused = (0..100).any(|_| {
            retaining(|| {
                let first = black_box(Box::new(7_u64));
                let address = &*first as *const u64 as usize;
                drop(first);
                address == &*black_box(Box::new(8_u64)) as *const u64 as usize
            })
        });
        assert!(reused);
    }
}
