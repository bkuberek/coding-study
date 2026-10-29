//! CPU time of the calling thread (docs/specs/performance-analysis.md#measurement): cases run on
//! one thread, so its clock counts only the code under measurement.

#[cfg(all(unix, target_pointer_width = "64"))]
mod thread_clock {
    use std::os::raw::c_int;

    #[repr(C)]
    struct Timespec {
        seconds: i64,
        nanoseconds: i64,
    }

    extern "C" {
        fn clock_gettime(clock: c_int, time: *mut Timespec) -> c_int;
    }

    #[cfg(target_os = "macos")]
    const CLOCK_THREAD_CPUTIME_ID: c_int = 16;
    #[cfg(not(target_os = "macos"))]
    const CLOCK_THREAD_CPUTIME_ID: c_int = 3;

    pub fn now_ns() -> u64 {
        let mut time = Timespec {
            seconds: 0,
            nanoseconds: 0,
        };
        // SAFETY: clock_gettime writes one timespec, whose layout matches on 64-bit Unix.
        if unsafe { clock_gettime(CLOCK_THREAD_CPUTIME_ID, &mut time) } != 0 {
            return 0;
        }
        (time.seconds as u64)
            .saturating_mul(1_000_000_000)
            .saturating_add(time.nanoseconds as u64)
    }
}

/// Nanoseconds of CPU time this thread has used; 0 where the clock is unavailable.
pub fn thread_cpu_ns() -> u64 {
    #[cfg(all(unix, target_pointer_width = "64"))]
    return thread_clock::now_ns();
    #[cfg(not(all(unix, target_pointer_width = "64")))]
    return 0;
}

#[cfg(test)]
mod tests {
    use super::thread_cpu_ns;

    #[test]
    fn grows_while_the_thread_computes() {
        let before = thread_cpu_ns();
        let mut total = 0_u64;
        for value in 0..5_000_000_u64 {
            total = total.wrapping_add(std::hint::black_box(value));
        }
        std::hint::black_box(total);
        assert!(thread_cpu_ns() > before);
    }
}
