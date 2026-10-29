//! What user code prints during one case (docs/specs/runners.md#execution-environment).
//!
//! File descriptors 1 and 2 are redirected to one pipe with `dup2`, because the standard
//! library's output capture is unstable and `eprintln!` writes to fd 2 directly. Standard output
//! and standard error share the pipe, so the text reads as it would in a terminal. `print!` is
//! buffered, so `io::stdout()` is flushed before the descriptors are restored.

use std::io::{self, Read, Write};
use std::thread::JoinHandle;

const MAX_OUTPUT_BYTES: usize = 4096;
const TRUNCATION_NOTICE: &str = "\n[output truncated at 4 KiB]\n";
/// Enough to tell whether the character at the limit is complete.
const KEPT_BYTES: usize = MAX_OUTPUT_BYTES + 4;

/// A running capture; `None` from [`start`] when the redirection is impossible, in which case
/// the case runs uncaptured.
pub struct Capture {
    saved: [i32; 2],
    drain: JoinHandle<(Vec<u8>, usize)>,
}

#[cfg(unix)]
mod fd {
    use std::os::raw::c_int;

    extern "C" {
        fn dup(fd: c_int) -> c_int;
        fn dup2(source: c_int, target: c_int) -> c_int;
        fn close(fd: c_int) -> c_int;
        fn pipe(fds: *mut c_int) -> c_int;
    }

    pub const STDOUT: c_int = 1;
    pub const STDERR: c_int = 2;

    pub fn duplicate(fd: c_int) -> Option<c_int> {
        // SAFETY: dup only reads its argument.
        let copy = unsafe { dup(fd) };
        (copy >= 0).then_some(copy)
    }

    pub fn redirect(source: c_int, target: c_int) -> bool {
        // SAFETY: dup2 replaces `target` with a copy of `source`, both owned by this module.
        unsafe { dup2(source, target) >= 0 }
    }

    pub fn close_fd(fd: c_int) {
        // SAFETY: called once per descriptor this module opened.
        unsafe {
            close(fd);
        }
    }

    /// The read and write ends of a new pipe.
    pub fn new_pipe() -> Option<(c_int, c_int)> {
        let mut fds: [c_int; 2] = [-1, -1];
        // SAFETY: pipe writes two descriptors into the array.
        let status = unsafe { pipe(fds.as_mut_ptr()) };
        (status == 0).then_some((fds[0], fds[1]))
    }
}

#[cfg(unix)]
pub fn start() -> Option<Capture> {
    use std::fs::File;
    use std::os::fd::FromRawFd;

    let _ = io::stdout().flush();
    let (reader, writer) = fd::new_pipe()?;
    let mut saved = [-1; 2];
    for (index, target) in [fd::STDOUT, fd::STDERR].into_iter().enumerate() {
        match fd::duplicate(target) {
            Some(copy) if fd::redirect(writer, target) => saved[index] = copy,
            other => {
                other.into_iter().for_each(fd::close_fd);
                restore(&saved[..index]);
                fd::close_fd(writer);
                fd::close_fd(reader);
                return None;
            }
        }
    }
    fd::close_fd(writer);
    // SAFETY: `reader` is a fresh descriptor that nothing else owns.
    let mut file = unsafe { File::from_raw_fd(reader) };
    let drain = std::thread::spawn(move || drain(&mut file));
    Some(Capture { saved, drain })
}

#[cfg(not(unix))]
pub fn start() -> Option<Capture> {
    None
}

/// Keeps the first bytes and reads the rest away, so a writer never blocks on a full pipe.
fn drain(reader: &mut impl Read) -> (Vec<u8>, usize) {
    let mut kept = Vec::new();
    let mut total = 0;
    let mut buffer = [0_u8; 16 * 1024];
    loop {
        match reader.read(&mut buffer) {
            Ok(0) | Err(_) => return (kept, total),
            Ok(count) => {
                total += count;
                let room = KEPT_BYTES.saturating_sub(kept.len()).min(count);
                kept.extend_from_slice(&buffer[..room]);
            }
        }
    }
}

#[cfg(unix)]
fn restore(saved: &[i32]) {
    for (index, target) in [fd::STDOUT, fd::STDERR]
        .into_iter()
        .enumerate()
        .take(saved.len())
    {
        fd::redirect(saved[index], target);
        fd::close_fd(saved[index]);
    }
}

impl Capture {
    /// Restores fds 1 and 2 and returns the captured text.
    pub fn stop(self) -> String {
        let _ = io::stdout().flush();
        #[cfg(unix)]
        restore(&self.saved);
        let (kept, total) = self.drain.join().unwrap_or_default();
        truncated(&kept, total)
    }
}

/// The text a case printed: everything up to 4096 bytes, else the first 4096 bytes without a
/// split character and the truncation notice.
pub fn stop(capture: Option<Capture>) -> String {
    capture.map(Capture::stop).unwrap_or_default()
}

fn truncated(kept: &[u8], total: usize) -> String {
    if total <= MAX_OUTPUT_BYTES {
        return String::from_utf8_lossy(kept).into_owned();
    }
    let cut = &kept[..MAX_OUTPUT_BYTES.min(kept.len())];
    let text = match std::str::from_utf8(cut) {
        Ok(text) => text,
        // The prefix up to a character split at the limit is valid UTF-8.
        Err(error) if error.error_len().is_none() => {
            std::str::from_utf8(&cut[..error.valid_up_to()]).unwrap_or_default()
        }
        Err(_) => return String::from_utf8_lossy(cut).into_owned() + TRUNCATION_NOTICE,
    };
    format!("{text}{TRUNCATION_NOTICE}")
}

#[cfg(test)]
mod tests {
    use super::{drain, truncated, MAX_OUTPUT_BYTES, TRUNCATION_NOTICE};

    #[test]
    fn short_output_is_kept_whole() {
        assert_eq!(truncated(b"hello\n", 6), "hello\n");
    }

    #[test]
    fn long_output_is_cut_at_4_kib_with_a_notice() {
        let text = "a".repeat(MAX_OUTPUT_BYTES + 10);
        let (kept, total) = drain(&mut text.as_bytes());
        let shown = truncated(&kept, total);
        assert_eq!(shown, "a".repeat(MAX_OUTPUT_BYTES) + TRUNCATION_NOTICE);
    }

    #[test]
    fn a_character_split_at_the_limit_is_dropped() {
        let text = "a".repeat(MAX_OUTPUT_BYTES - 1) + "üü";
        let (kept, total) = drain(&mut text.as_bytes());
        let shown = truncated(&kept, total);
        assert_eq!(shown, "a".repeat(MAX_OUTPUT_BYTES - 1) + TRUNCATION_NOTICE);
    }
}
