//! Test mode (docs/specs/runners.md#event-stream): runs each job's cases against the targets the
//! bridge registered, plus the panic handling bench mode shares.
//!
//! A panic in user code is caught per call. The panic hook replaces the default one, which would
//! print to standard error, and keeps the message, the location and a backtrace, whose frames in
//! the target's file become the error's trace.

use std::any::Any;
use std::backtrace::Backtrace;
use std::cell::RefCell;
use std::panic::{self, AssertUnwindSafe};
use std::path::Path;
use std::time::Instant;

use crate::alloc;
use crate::capture;
use crate::events::{Events, Outcome, Status, UserError};
use crate::json::Json;
use crate::request::{CallInput, Job, Kind};
use crate::{Args, Class, Entry, Target};

/// A panic outside user code: the runner itself failed.
pub const EXIT_INTERNAL_ERROR: i32 = 70;
const MAX_TRACE_LINES: usize = 10;
/// The error type of every panic: Rust panics carry a message, not a type.
const PANIC_TYPE: &str = "panic";
/// The index of the constructor in an operation sequence.
const CONSTRUCTOR_OP: usize = 0;

struct PanicRecord {
    message: String,
    location: Option<(String, u32)>,
    backtrace: Backtrace,
}

thread_local! {
    static LAST_PANIC: RefCell<Option<PanicRecord>> = const { RefCell::new(None) };
}

pub fn install_panic_hook() {
    panic::set_hook(Box::new(|info| {
        let record = PanicRecord {
            message: panic_text(info.payload()),
            location: info
                .location()
                .map(|location| (location.file().to_string(), location.line())),
            backtrace: Backtrace::force_capture(),
        };
        LAST_PANIC.with(|slot| *slot.borrow_mut() = Some(record));
    }));
}

/// The message of a panic payload: `panic!("...")` gives a `&str` or a `String`.
pub fn panic_text(payload: &(dyn Any + Send)) -> String {
    payload
        .downcast_ref::<&str>()
        .map(|text| text.to_string())
        .or_else(|| payload.downcast_ref::<String>().cloned())
        .unwrap_or_else(|| "Box<dyn Any>".to_string())
}

/// The last panic on this thread as an `error` whose trace keeps the frames in `file`.
pub fn take_panic(file: &str) -> UserError {
    let Some(record) = LAST_PANIC.with(|slot| slot.borrow_mut().take()) else {
        return UserError::new(PANIC_TYPE, "the call panicked");
    };
    let mut error = UserError::new(PANIC_TYPE, record.message);
    let panicked_at = record
        .location
        .as_ref()
        .map(|(path, line)| (path.as_str(), *line));
    let lines = user_trace(&record.backtrace.to_string(), file, panicked_at);
    let start = lines.len().saturating_sub(MAX_TRACE_LINES);
    error.trace = lines[start..].join("\n");
    error
}

fn file_name(path: &str) -> String {
    Path::new(path).file_name().map_or_else(
        || path.to_string(),
        |name| name.to_string_lossy().into_owned(),
    )
}

/// One frame of a `std::backtrace::Backtrace`'s text: a numbered symbol line, followed by an
/// `at <file>:<line>:<column>` line when the location is known.
struct Frame<'a> {
    symbol: &'a str,
    location: Option<(&'a str, u32)>,
}

fn frames(backtrace: &str) -> Vec<Frame<'_>> {
    let mut frames: Vec<Frame> = Vec::new();
    for line in backtrace.lines() {
        let trimmed = line.trim_start();
        if let Some(location) = trimmed.strip_prefix("at ") {
            let mut parts = location.rsplitn(3, ':');
            let (_column, number, path) = (parts.next(), parts.next(), parts.next());
            let number = number.and_then(|number| number.parse().ok());
            if let (Some(frame), Some(path), Some(number)) = (frames.last_mut(), path, number) {
                frame.location = Some((path, number));
            }
        } else {
            let symbol = trimmed.split_once(": ").map_or(trimmed, |(_, name)| name);
            frames.push(Frame {
                symbol,
                location: None,
            });
        }
    }
    frames
}

/// The frames of a backtrace in `file`, innermost last, like the other runners:
/// `two_sum.rs:7 in two_sum`, `lru_cache.rs:31 in LRUCache::get`.
///
/// In a release build the innermost user function is often inlined into its caller and listed
/// without a location; the panic's own location (indexing, arithmetic overflow and `unwrap`
/// report the user's line) stands in for it.
pub fn user_trace(backtrace: &str, file: &str, panicked_at: Option<(&str, u32)>) -> Vec<String> {
    let frames = frames(backtrace);
    let name = file_name(file);
    let line_of = |frame: &Frame| {
        frame
            .location
            .filter(|(path, _)| *path == file)
            .map(|(_, line)| line)
    };
    let innermost = frames.iter().position(|frame| line_of(frame).is_some());
    let mut lines = Vec::new();
    if let Some((_, line)) = panicked_at.filter(|(path, _)| *path == file) {
        if innermost.and_then(|index| line_of(&frames[index])) != Some(line) {
            let inlined = innermost
                .and_then(|index| index.checked_sub(1))
                .map(|index| &frames[index])
                .filter(|frame| frame.location.is_none());
            lines.push(match inlined {
                Some(frame) => format!("{name}:{line} in {}", function(frame.symbol)),
                None => format!("{name}:{line}"),
            });
        }
    }
    for frame in &frames {
        if let Some(line) = line_of(frame) {
            lines.push(format!("{name}:{line} in {}", function(frame.symbol)));
        }
    }
    lines.reverse();
    lines
}

/// `two_sum_test::user::LRUCache::get::h0123456789abcdef` as `LRUCache::get`: the crate and the
/// bridge's module are internal.
fn function(symbol: &str) -> String {
    let symbol = match symbol.rsplit_once("::h") {
        Some((name, hash)) if hash.len() == 16 && hash.bytes().all(|b| b.is_ascii_hexdigit()) => {
            name
        }
        _ => symbol,
    };
    let parts: Vec<&str> = symbol.split("::").collect();
    if symbol.starts_with('<') || parts.len() <= 2 {
        return symbol.to_string();
    }
    parts[2..].join("::")
}

/// A call into user code with its duration; a panic becomes an error with the user's frames.
pub fn timed<R>(file: &str, call: impl FnOnce() -> R) -> (Result<R, UserError>, u64) {
    let started = Instant::now();
    let result = alloc::checked(|| panic::catch_unwind(AssertUnwindSafe(call)));
    let duration = elapsed_ns(started);
    (result.map_err(|_| take_panic(file)), duration)
}

pub fn elapsed_ns(started: Instant) -> u64 {
    u64::try_from(started.elapsed().as_nanos()).unwrap_or(u64::MAX)
}

/// A target that can run a job of `kind`, or the job's `load_error`.
pub fn bind<'a>(targets: &'a [Target], id: &str, kind: Kind) -> Result<&'a Target, UserError> {
    let target = targets
        .iter()
        .find(|target| target.id == id)
        .ok_or_else(|| {
            UserError::new(
                "LoadError",
                format!("target \"{id}\" is not part of this build"),
            )
        })?;
    match (&target.entry, kind) {
        (
            Entry::Unavailable {
                error_type,
                message,
            },
            _,
        ) => Err(UserError::new(error_type, *message)),
        (Entry::Function(_), Kind::Function) | (Entry::Class(_), Kind::Class) => Ok(target),
        _ => Err(UserError::new(
            "LoadError",
            format!("target \"{id}\" was built for another kind of problem"),
        )),
    }
}

pub fn run_test_jobs(targets: &[Target], jobs: &[Job], events: &mut Events) {
    for job in jobs {
        events.job_start(&job.job_id);
        match bind(targets, &job.target, job.kind) {
            Err(error) => events.load_error(&job.job_id, &error),
            Ok(target) => {
                for case in &job.cases {
                    events.case_start(&job.job_id, &case.id);
                    events.case_result(&job.job_id, &case.id, run_case(target, &case.input));
                }
            }
        }
        events.job_end(&job.job_id);
    }
}

/// One case as `cstudy test` runs it, capturing what the code prints. Bench check calls run the
/// same way.
pub fn run_case(target: &Target, input: &CallInput) -> Outcome {
    let output = capture::start();
    let mut outcome = match (&target.entry, input) {
        (Entry::Function(function), CallInput::Named(fields)) => {
            match function(&Args::Named(fields)) {
                Err(error) => Outcome::raised(UserError::invalid_input(error.0), 0),
                Ok(call) => {
                    let (result, duration) = timed(target.file, call);
                    match result.map(|value| value.encode()) {
                        Err(error) => Outcome::raised(error, duration),
                        Ok(Ok(json)) => Outcome::returned(json, duration),
                        Ok(Err(reason)) => Outcome::invalid(reason, duration),
                    }
                }
            }
        }
        (Entry::Class(class), CallInput::Ops { ops, args }) => {
            Operations::new(target.file, class).run(ops, args)
        }
        (Entry::Function(_), CallInput::Ops { .. }) => Outcome::raised(
            UserError::invalid_input("a function job takes arguments, not an operation sequence"),
            0,
        ),
        _ => Outcome::raised(
            UserError::invalid_input("a class job takes an operation sequence, not arguments"),
            0,
        ),
    };
    outcome.stdout = capture::stop(output);
    outcome
}

/// One case of a class kind: the constructor, then each operation on the new instance.
struct Operations<'a> {
    file: &'a str,
    class: &'a Class,
    outputs: Vec<Json>,
    duration: u64,
}

impl<'a> Operations<'a> {
    fn new(file: &'a str, class: &'a Class) -> Self {
        Operations {
            file,
            class,
            outputs: Vec::new(),
            duration: 0,
        }
    }

    fn run(mut self, ops: &[String], args: &[Vec<Json>]) -> Outcome {
        if ops.len() != args.len() {
            let message = format!("{} operations but {} argument lists", ops.len(), args.len());
            return self.failed(CONSTRUCTOR_OP, UserError::invalid_input(message));
        }
        let Some(first) = ops.first() else {
            let message = "a class job takes an operation sequence, not arguments";
            return self.failed(CONSTRUCTOR_OP, UserError::invalid_input(message));
        };
        if first != self.class.name {
            let message = format!(
                "operation 0 must be \"{}\", got \"{first}\"",
                self.class.name
            );
            return self.failed(CONSTRUCTOR_OP, UserError::invalid_input(message));
        }
        let make = match (self.class.construct)(&Args::Positional(&args[CONSTRUCTOR_OP])) {
            Ok(make) => make,
            Err(error) => return self.failed(CONSTRUCTOR_OP, UserError::invalid_input(error.0)),
        };
        let (instance, duration) = timed(self.file, make);
        self.duration += duration;
        let mut instance = match instance {
            Ok(instance) => instance,
            Err(error) => return self.failed(CONSTRUCTOR_OP, error),
        };
        self.outputs.push(Json::Null);
        for (index, (op, arguments)) in ops.iter().zip(args).enumerate().skip(1) {
            let call = match (self.class.method)(op, &Args::Positional(arguments)) {
                Ok(call) => call,
                Err(error) if error == crate::InputError::unknown_op(op) => {
                    let message = format!("unknown operation \"{op}\" at index {index}");
                    return self.failed(index, UserError::invalid_input(message));
                }
                Err(error) => return self.failed(index, UserError::invalid_input(error.0)),
            };
            let (result, duration) = timed(self.file, || call(&mut *instance));
            self.duration += duration;
            let value = match result {
                Ok(value) => value,
                Err(error) => return self.failed(index, error),
            };
            match value.encode() {
                Ok(json) => self.outputs.push(json),
                Err(reason) => {
                    let reason = format!("operation {index} ({op}): {reason}");
                    return Outcome::invalid(reason, self.duration);
                }
            }
        }
        Outcome::returned(Json::Array(self.outputs), self.duration)
    }

    fn failed(self, index: usize, error: UserError) -> Outcome {
        Outcome {
            status: Status::Error {
                error,
                op: Some((index, self.outputs)),
            },
            duration_ns: self.duration,
            stdout: String::new(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{function, user_trace};

    const FILE: &str = "/ws/rust/practice/lru_cache.rs";
    /// The shape of a release build's backtrace: `touch` was inlined into `get` and has no
    /// location of its own.
    const BACKTRACE: &str = "   0: std::backtrace::Backtrace::force_capture
             at /rustc/abc/library/std/src/backtrace.rs:312:9
   1: core::panicking::panic_bounds_check
             at /rustc/abc/library/core/src/panicking.rs:276:5
   2: touch
   3: lru_cache_test::user::LRUCache::get
             at /ws/rust/practice/lru_cache.rs:20:15
   4: lru_cache_test::user_method::{{closure}}
             at /ws/.cs/build/rust/test/lru_cache/main.rs:40:5
   5: main
";

    #[test]
    fn keeps_the_frames_in_the_target_file_innermost_last() {
        assert_eq!(
            user_trace(BACKTRACE, FILE, Some((FILE, 31))),
            [
                "lru_cache.rs:20 in LRUCache::get",
                "lru_cache.rs:31 in touch"
            ]
        );
    }

    #[test]
    fn the_panic_location_is_not_repeated() {
        assert_eq!(
            user_trace(BACKTRACE, FILE, Some((FILE, 20))),
            ["lru_cache.rs:20 in LRUCache::get"]
        );
    }

    #[test]
    fn a_panic_elsewhere_keeps_only_the_frames() {
        let panicked_at = Some(("/rustc/abc/library/core/src/option.rs", 9));
        assert_eq!(
            user_trace(BACKTRACE, FILE, panicked_at),
            ["lru_cache.rs:20 in LRUCache::get"]
        );
    }

    #[test]
    fn without_frames_the_panic_location_is_the_trace() {
        assert_eq!(
            user_trace("   0: main\n", FILE, Some((FILE, 7))),
            ["lru_cache.rs:7"]
        );
        assert!(user_trace("   0: main\n", FILE, None).is_empty());
    }

    #[test]
    fn function_names_drop_the_crate_the_module_and_the_hash() {
        assert_eq!(
            function("two_sum_test::user::two_sum::h0123456789abcdef"),
            "two_sum"
        );
        assert_eq!(
            function("x_test::ref_hash_map::helper::{{closure}}"),
            "helper::{{closure}}"
        );
        assert_eq!(function("main"), "main");
    }
}
