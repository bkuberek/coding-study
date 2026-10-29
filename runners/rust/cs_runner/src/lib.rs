//! The Rust runner library (docs/specs/runners.md#rust-build-details).
//!
//! Rust has no reflection, so the CLI generates a typed bridge per problem. The bridge brings the
//! user's file and each reference in as `#[path]` modules, decodes every argument with its
//! declared type, calls the code, and hands the result back as a boxed [`Encode`]. This crate
//! owns the protocol, the codec, the case loop, bench mode, output capture and memory figures:
//!
//! ```ignore
//! fn user_call(args: &cs_runner::Args) -> Result<cs_runner::Call, cs_runner::InputError> {
//!     let nums: Vec<i32> = args.named("nums")?;
//!     let target: i32 = args.named("target")?;
//!     Ok(Box::new(move || {
//!         let output: Vec<i32> = user::two_sum(nums, target);
//!         cs_runner::output(output)
//!     }))
//! }
//!
//! static TARGETS: &[cs_runner::Target] = &[cs_runner::Target {
//!     id: "user",
//!     file: "/ws/rust/practice/two_sum.rs",
//!     entry: cs_runner::Entry::Function(user_call),
//! }];
//!
//! fn main() {
//!     cs_runner::main(TARGETS)
//! }
//! ```
//!
//! A concurrent problem's class is shared by the worker threads of its stress runs, so its
//! bridge registers an [`Entry::Concurrent`]: methods take `&self`, every decoded call is `Send`,
//! and [`shared`] requires the class to be `Send + Sync`.
//!
//! Exit codes: 0 once `bye` is written; 2 for a request that cannot be run; 3 after
//! `restart_requested`.

mod alloc;
mod bench;
mod capture;
mod clock;
mod codec;
mod events;
mod harness;
pub mod json;
mod nodes;
mod request;
mod stress;

use std::any::Any;
use std::cell::RefCell;
use std::fs::File;
use std::rc::Rc;
use std::sync::Arc;

pub use alloc::retaining;
pub use codec::{Decode, Encode};
pub use nodes::{Identity, IndexIn, NoAlias, Nodes, Shared, Single, ValueOf};

use events::Events;
use json::Json;

/// Cases run on this thread; deep recursion in user code needs the room.
const CASE_STACK_BYTES: usize = 256 * 1024 * 1024;
const CASE_THREAD: &str = "cs-runner-cases";
const EXIT_COMPLETED: i32 = 0;
const EXIT_BAD_REQUEST: i32 = 2;
/// After `restart_requested`: a stress run left worker threads running.
const EXIT_RESTART: i32 = 3;

/// A case input that does not fit the declared parameters (error type `InvalidInput`).
#[derive(Debug, PartialEq)]
pub struct InputError(pub String);

impl InputError {
    pub fn unknown_op(op: &str) -> Self {
        InputError(format!("unknown operation \"{op}\""))
    }
}

/// One call into user code, its arguments already decoded.
pub type Call = Box<dyn FnOnce() -> Box<dyn Encode>>;

/// Decodes a function's arguments and returns the call.
pub type Function = fn(&Args) -> Result<Call, InputError>;

/// Creates an instance of a class kind.
pub type Construct = Box<dyn FnOnce() -> Box<dyn Any>>;

/// One method call on the instance that the class's [`Construct`] created.
pub type Method = Box<dyn FnOnce(&mut dyn Any) -> Box<dyn Encode>>;

/// A design or progressive class: its constructor and its methods by canonical name.
pub struct Class {
    pub name: &'static str,
    pub construct: fn(&Args) -> Result<Construct, InputError>,
    /// A `match` on the operation name; [`InputError::unknown_op`] for any other name.
    pub method: fn(&str, &Args) -> Result<Method, InputError>,
}

/// The instance of a concurrent class, which the worker threads share.
pub type Instance = Arc<dyn Any + Send + Sync>;

/// Creates the shared instance of a concurrent class.
pub type SharedConstruct = Box<dyn FnOnce() -> Instance + Send>;

/// One method call on a concurrent class's instance, on whichever thread runs it.
pub type SharedMethod = Box<dyn FnOnce(&(dyn Any + Send + Sync)) -> Box<dyn Encode> + Send>;

/// A concurrent class (docs/specs/runners.md#concurrent-jobs): its sequential cases run like a
/// class's, its stress runs call the methods of one instance from several threads.
pub struct Concurrent {
    pub name: &'static str,
    pub construct: fn(&Args) -> Result<SharedConstruct, InputError>,
    /// A `match` on the operation name; [`InputError::unknown_op`] for any other name.
    pub method: fn(&str, &Args) -> Result<SharedMethod, InputError>,
}

pub enum Entry {
    Function(Function),
    Class(Class),
    Concurrent(Concurrent),
    /// A target that cannot run: its bridge code did not compile (a missing symbol, another
    /// signature) or it uses a type Rust does not support yet. The CLI built the binary without
    /// it, and each of its jobs gets this `load_error`.
    Unavailable {
        error_type: &'static str,
        message: &'static str,
    },
}

pub struct Target {
    /// The `target.compiled` id of the request: `user` or `ref/<approach>`.
    pub id: &'static str,
    /// The source file as the bridge's `#[path]` names it; error traces keep its frames.
    pub file: &'static str,
    pub entry: Entry,
}

/// The arguments of one call: by canonical parameter name for functions, by position for
/// constructors and methods.
pub enum Args<'a> {
    Named(&'a [(String, Json)]),
    Positional(&'a [Json]),
}

impl Args<'_> {
    fn value(&self, index: usize, name: &str) -> Result<&Json, InputError> {
        let value = match self {
            Args::Named(fields) => fields
                .iter()
                .find(|(key, _)| key == name)
                .map(|(_, value)| value),
            Args::Positional(values) => values.get(index),
        };
        value.ok_or_else(|| InputError(format!("missing input {name}")))
    }

    /// A function's argument `name`.
    pub fn named<T: Decode>(&self, name: &str) -> Result<T, InputError> {
        self.decoded(0, name)
    }

    /// Argument `index`, declared as `name`, of a constructor or method.
    pub fn at<T: Decode>(&self, index: usize, name: &str) -> Result<T, InputError> {
        self.decoded(index, name)
    }

    fn decoded<T: Decode>(&self, index: usize, name: &str) -> Result<T, InputError> {
        T::decode(self.value(index, name)?)
            .map_err(|message| InputError(format!("{name}: {message}")))
    }

    /// `ref_of`: the node of `within` (the parameter `of`) whose value the argument gives.
    pub fn node_in<S: Shared>(
        &self,
        index: usize,
        name: &str,
        within: &S,
        of: &str,
    ) -> Result<Option<Rc<RefCell<S::Node>>>, InputError> {
        let value = self.value(index, name)?;
        nodes::node_of(value, within, of)
            .map_err(|message| InputError(format!("{name}: {message}")))
    }

    /// Fails unless an operation passes exactly `expected` arguments.
    pub fn count(&self, expected: usize, op: &str) -> Result<(), InputError> {
        let given = match self {
            Args::Named(fields) => fields.len(),
            Args::Positional(values) => values.len(),
        };
        if given != expected {
            return Err(InputError(format!(
                "\"{op}\" takes {expected} arguments, the case gives {given}"
            )));
        }
        Ok(())
    }
}

/// Boxes a call's result for encoding.
pub fn output<T: Encode + 'static>(value: T) -> Box<dyn Encode> {
    Box::new(value)
}

/// Boxes a new instance of a class kind.
pub fn object<T: 'static>(instance: T) -> Box<dyn Any> {
    Box::new(instance)
}

/// The instance a method runs on, as the type the bridge's constructor created.
pub fn instance<T: 'static>(object: &mut dyn Any) -> &mut T {
    object
        .downcast_mut::<T>()
        .expect("the bridge calls methods on the instance its constructor created")
}

/// Shares a new instance of a concurrent class with the worker threads. The bound is where the
/// compiler checks thread safety: a class with a `RefCell` or `Rc` field fails to build here.
pub fn shared<T: Send + Sync + 'static>(instance: T) -> Instance {
    Arc::new(instance)
}

/// The shared instance a method runs on, as the type the bridge's constructor created.
pub fn shared_instance<T: 'static>(object: &(dyn Any + Send + Sync)) -> &T {
    object
        .downcast_ref::<T>()
        .expect("the bridge calls methods on the instance its constructor created")
}

/// The runner's entry point: `--request R --out O`.
pub fn main(targets: &'static [Target]) -> ! {
    std::process::exit(run(targets))
}

fn run(targets: &'static [Target]) -> i32 {
    let arguments: Vec<String> = std::env::args().skip(1).collect();
    let (Some(request_path), Some(out_path)) =
        (flag(&arguments, "--request"), flag(&arguments, "--out"))
    else {
        eprintln!("usage: cs-rust-runner --request R --out O");
        return EXIT_BAD_REQUEST;
    };
    let mut events = match File::create(out_path) {
        Ok(file) => Events::new(file),
        Err(error) => {
            eprintln!("cs-rust-runner: {error}");
            return EXIT_BAD_REQUEST;
        }
    };
    events.hello();
    let request = match std::fs::read_to_string(request_path)
        .map_err(|error| error.to_string())
        .and_then(|text| request::parse_request(&text))
    {
        Ok(request) => request,
        Err(error) => {
            eprintln!("cs-rust-runner: bad request: {error}");
            return EXIT_BAD_REQUEST;
        }
    };
    harness::install_panic_hook();
    let cases = std::thread::Builder::new()
        .name(CASE_THREAD.into())
        .stack_size(CASE_STACK_BYTES)
        .spawn(move || {
            let completed = match request.mode {
                request::Mode::Test => harness::run_test_jobs(targets, &request.jobs, &mut events),
                request::Mode::Bench => {
                    bench::run_bench_jobs(targets, &request.jobs, &mut events);
                    true
                }
            };
            if completed {
                events.bye();
            }
            completed
        });
    match cases.map(std::thread::JoinHandle::join) {
        Ok(Ok(true)) => EXIT_COMPLETED,
        Ok(Ok(false)) => EXIT_RESTART,
        Ok(Err(panic)) => {
            eprintln!(
                "cs-rust-runner: internal error: {}",
                harness::panic_text(&*panic)
            );
            harness::EXIT_INTERNAL_ERROR
        }
        Err(error) => {
            eprintln!("cs-rust-runner: cannot start the case thread: {error}");
            harness::EXIT_INTERNAL_ERROR
        }
    }
}

fn flag<'a>(arguments: &'a [String], name: &str) -> Option<&'a str> {
    arguments
        .iter()
        .position(|argument| argument == name)
        .and_then(|index| arguments.get(index + 1))
        .map(String::as_str)
}
