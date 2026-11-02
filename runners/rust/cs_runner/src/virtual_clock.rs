//! Cases on the virtual clock (docs/specs/runners.md#virtual-clock-and-stress-in-project-jobs).
//!
//! Each case runs on a tokio runtime of its own, current-thread and built with its clock paused,
//! from the constructor on: time moves only when every task waits, and then jumps to the next
//! timer. Each operation is one `block_on` on that runtime: the call, awaited when the method is
//! an `async fn`, then the settle step, which lets every task run until each one waits.
//!
//! tokio has no call that waits until every task waits. Its park hook does run exactly then: the
//! current-thread scheduler calls `on_thread_park` when no task is ready, no task yielded and the
//! `block_on` future was not woken, right before it parks, and only that park moves a paused
//! clock. So settling waits for the hook to wake it. A timer due at that instant has already
//! fired, since tokio fires a timer registered at or before the current instant at once and
//! processes the due timers right after the clock moves.
//!
//! A deadlock is an operation that waits while no task can run and no timer is due. A paused
//! clock would then park for good, so each wait races a sentinel timer about 400 days ahead, at a
//! multiple of 2^30 ms, where tokio's timer wheel fires it without stopping on the way. When the
//! sentinel fires first, the case is `stalled` at the virtual time of the last idle park.
//!
//! When a case ends, its runtime is dropped, and with it every task still pending, as a dropped
//! runtime drops them in a tokio test.

use std::any::Any;
use std::collections::HashMap;
use std::future::{poll_fn, Future};
use std::panic::{self, AssertUnwindSafe};
use std::pin::{pin, Pin};
use std::sync::{Arc, Mutex, MutexGuard, PoisonError};
use std::task::{Poll, Waker};
use std::time::Duration;

use tokio::runtime::{Builder, Runtime};
use tokio::task::{JoinError, JoinHandle};
use tokio::time::Instant;

use crate::codec::Encode;
use crate::events::{Outcome, Status, UserError};
use crate::harness::{panic_text, take_panic, timed};
use crate::json::Json;
use crate::{Args, Concurrent, Construct, InputError, Instance};

const ADVANCE: &str = "@advance";
const SPAWN: &str = "@spawn";
const JOIN: &str = "@join";
const NOW: &str = "@now";
/// The index of the constructor in an operation sequence.
const CONSTRUCTOR_OP: usize = 0;
/// How far ahead of a wait its sentinel lies, at least: no content waits this long.
const SENTINEL_HORIZON_MS: u64 = 1 << 35;
/// The sentinel's instant is a multiple of the slot of the timer wheel's top level, so the wheel
/// fires it in one step instead of moving it down level by level, each a park of its own.
const SENTINEL_ALIGNMENT_MS: u64 = 1 << 30;

/// The result of an operation that a spawned task hands back to the case.
pub type SendOutput = Box<dyn Encode + Send>;

/// An operation's call on an owned instance: a future that borrows the instance.
pub type OwnedFuture<'a> = Pin<Box<dyn Future<Output = Box<dyn Encode>> + 'a>>;

/// One method call on the instance that an owned class's constructor created.
pub type OwnedCall = Box<dyn for<'a> FnOnce(&'a mut dyn Any) -> OwnedFuture<'a>>;

/// An operation's call on a shared instance, which `@spawn` can hand to `tokio::spawn`.
pub type SharedFuture = Pin<Box<dyn Future<Output = SendOutput> + Send>>;

/// One method call on a shared instance, which the call keeps alive.
pub type SharedCall = Box<dyn FnOnce(Instance) -> SharedFuture>;

/// The entry class of a project on the virtual clock.
pub enum ClockClass {
    /// Owned by its case: methods may take `&mut self`, and no task can share the instance.
    Owned {
        name: &'static str,
        construct: fn(&Args) -> Result<Construct, InputError>,
        /// A `match` on the operation name; [`InputError::unknown_op`] for any other name.
        call: fn(&str, &Args) -> Result<OwnedCall, InputError>,
    },
    /// Shared from the first level whose cases spawn a task or have stress cases: methods take
    /// `&self`. `class` calls them from the worker threads of stress runs, on the real clock.
    Shared {
        class: Concurrent,
        /// A `match` on the operation name; [`InputError::unknown_op`] for any other name.
        call: fn(&str, &Args) -> Result<SharedCall, InputError>,
    },
}

impl ClockClass {
    fn name(&self) -> &'static str {
        match self {
            ClockClass::Owned { name, .. } => name,
            ClockClass::Shared { class, .. } => class.name,
        }
    }

    /// The class the worker threads of a stress run call; None when the instance is owned.
    pub fn concurrent(&self) -> Option<&Concurrent> {
        match self {
            ClockClass::Owned { .. } => None,
            ClockClass::Shared { class, .. } => Some(class),
        }
    }
}

/// Boxes an owned class's call; the bound gives the closure the signature whose future borrows
/// the instance it is handed.
pub fn owned_call<F>(call: F) -> OwnedCall
where
    F: for<'a> FnOnce(&'a mut dyn Any) -> OwnedFuture<'a> + 'static,
{
    Box::new(call)
}

/// Boxes a shared class's call.
pub fn shared_call<F, R>(call: F) -> SharedCall
where
    F: FnOnce(Instance) -> R + 'static,
    R: Future<Output = SendOutput> + Send + 'static,
{
    Box::new(move |instance| Box::pin(call(instance)))
}

/// Boxes a call's result for encoding on the case's thread, from whichever task made it.
pub fn sendable<T: Encode + Send + 'static>(value: T) -> SendOutput {
    Box::new(value)
}

thread_local! {
    /// The runtime of a stress worker thread, on the real clock.
    static WORKER_RUNTIME: Runtime = Builder::new_current_thread()
        .enable_time()
        .build()
        .expect("a stress worker builds a current-thread runtime");
}

/// Runs an `async fn` to its end on the calling thread: a stress worker calls the asynchronous
/// methods of a virtual-clock project so, on the real clock, as Kotlin's workers call `suspend`
/// methods in `runBlocking`.
pub fn block_on<F: Future>(future: F) -> F::Output {
    WORKER_RUNTIME.with(|runtime| runtime.block_on(future))
}

/// One case on the virtual clock: the constructor, then each operation, harness operations
/// included.
pub fn run(file: &str, class: &ClockClass, ops: &[String], args: &[Vec<Json>]) -> Outcome {
    if ops.len() != args.len() {
        let message = format!("{} operations but {} argument lists", ops.len(), args.len());
        return Ended::Error(UserError::invalid_input(message)).outcome(
            CONSTRUCTOR_OP,
            Vec::new(),
            0,
        );
    }
    let first = ops.first().map(String::as_str);
    if first != Some(class.name()) {
        let message = format!(
            "operation 0 must be \"{}\", got \"{}\"",
            class.name(),
            first.unwrap_or_default()
        );
        return Ended::Error(UserError::invalid_input(message)).outcome(
            CONSTRUCTOR_OP,
            Vec::new(),
            0,
        );
    }
    let mut case = match Case::new(file) {
        Ok(case) => case,
        Err(error) => {
            let error =
                UserError::new("RuntimeError", format!("cannot build the runtime: {error}"));
            return Outcome::raised(error, 0);
        }
    };
    let (index, ended, held) = case.operations(class, ops, args);
    let Case {
        runtime,
        tasks,
        outputs,
        duration,
        ..
    } = case;
    end(runtime, tasks, held);
    match ended {
        None => Outcome::returned(Json::Array(outputs), duration),
        Some(ended) => ended.outcome(index, outputs, duration),
    }
}

/// Why a case ended before its last operation.
enum Ended {
    Error(UserError),
    Invalid(String),
    Deadlock(String),
}

impl Ended {
    fn outcome(self, index: usize, outputs: Vec<Json>, duration_ns: u64) -> Outcome {
        let status = match self {
            Ended::Error(error) => Status::Error {
                error,
                op: Some((index, outputs)),
            },
            Ended::Invalid(reason) => Status::InvalidOutput(reason),
            Ended::Deadlock(reason) => Status::Deadlocked {
                reason,
                op: (index, outputs),
            },
        };
        Outcome {
            status,
            duration_ns,
            stdout: String::new(),
            stress: Vec::new(),
        }
    }
}

fn invalid_input(message: impl Into<String>) -> Ended {
    Ended::Error(UserError::invalid_input(message))
}

/// The instance a case's calls run on.
enum Held {
    Owned(Box<dyn Any>),
    Shared(Instance),
}

/// What the park hook and the settle step share.
#[derive(Default)]
struct Idle {
    /// The settle step waiting for the next idle park.
    waiter: Option<Waker>,
    /// Set by the idle park that woke the waiter.
    settled: bool,
    /// The virtual time of the last idle park.
    parked_at: Option<Instant>,
}

fn lock(idle: &Mutex<Idle>) -> MutexGuard<'_, Idle> {
    idle.lock().unwrap_or_else(PoisonError::into_inner)
}

/// The park hook: every task waits.
fn parked(idle: &Mutex<Idle>) {
    let waiter = {
        let mut idle = lock(idle);
        idle.parked_at = Some(Instant::now());
        let waiter = idle.waiter.take();
        idle.settled = waiter.is_some();
        waiter
    };
    if let Some(waiter) = waiter {
        waiter.wake();
    }
}

/// Lets every task run until each one waits, without moving the clock.
fn settle(idle: &Mutex<Idle>) -> impl Future<Output = ()> + '_ {
    poll_fn(move |context| {
        let mut idle = lock(idle);
        if std::mem::take(&mut idle.settled) {
            return Poll::Ready(());
        }
        idle.waiter = Some(context.waker().clone());
        Poll::Pending
    })
}

/// Awaits `future` while the clock moves to each due timer; None when every task waits while no
/// timer is due, a deadlock.
async fn wait<F: Future>(future: F, start: Instant) -> Option<F::Output> {
    let mut sentinel = pin!(tokio::time::sleep_until(sentinel(start)));
    let mut future = pin!(future);
    poll_fn(|context| {
        if let Poll::Ready(value) = future.as_mut().poll(context) {
            return Poll::Ready(Some(value));
        }
        sentinel.as_mut().poll(context).map(|()| None)
    })
    .await
}

fn sentinel(start: Instant) -> Instant {
    let now = millis(Instant::now() - start);
    let due = (now + SENTINEL_HORIZON_MS).div_ceil(SENTINEL_ALIGNMENT_MS) * SENTINEL_ALIGNMENT_MS;
    start + Duration::from_millis(due)
}

fn millis(duration: Duration) -> u64 {
    u64::try_from(duration.as_millis()).unwrap_or(u64::MAX)
}

struct Case<'a> {
    file: &'a str,
    runtime: Runtime,
    idle: Arc<Mutex<Idle>>,
    /// The paused clock's start, the start of the timer wheel's ticks too.
    start: Instant,
    outputs: Vec<Json>,
    duration: u64,
    tasks: HashMap<String, JoinHandle<SendOutput>>,
}

impl<'a> Case<'a> {
    fn new(file: &'a str) -> std::io::Result<Self> {
        let idle = Arc::new(Mutex::new(Idle::default()));
        let hook = Arc::clone(&idle);
        let runtime = Builder::new_current_thread()
            .enable_time()
            .start_paused(true)
            .on_thread_park(move || parked(&hook))
            .build()?;
        let start = {
            let _context = runtime.enter();
            Instant::now()
        };
        Ok(Case {
            file,
            runtime,
            idle,
            start,
            outputs: Vec::new(),
            duration: 0,
            tasks: HashMap::new(),
        })
    }

    /// Runs the constructor and each operation; the index of the operation that ended the case
    /// early and why, and the instance, which outlives the calls that borrow it.
    fn operations(
        &mut self,
        class: &ClockClass,
        ops: &[String],
        args: &[Vec<Json>],
    ) -> (usize, Option<Ended>, Option<Held>) {
        let mut held = match self.construct(class, &args[CONSTRUCTOR_OP]) {
            Ok(held) => held,
            Err(ended) => return (CONSTRUCTOR_OP, Some(ended), None),
        };
        self.outputs.push(Json::Null);
        for (index, (op, arguments)) in ops.iter().zip(args).enumerate().skip(1) {
            let output = match op.as_str() {
                ADVANCE => self.advance(arguments),
                NOW => Ok(self.now()),
                SPAWN => self.spawn(class, &held, index, arguments),
                JOIN => self.join(index, arguments),
                _ => self.call(class, &mut held, index, op, arguments),
            };
            match output {
                Ok(json) => self.outputs.push(json),
                Err(ended) => return (index, Some(ended), Some(held)),
            }
        }
        (ops.len(), None, Some(held))
    }

    fn construct(&mut self, class: &ClockClass, args: &[Json]) -> Result<Held, Ended> {
        let arguments = Args::Positional(args);
        match class {
            ClockClass::Owned { construct, .. } => {
                let make = construct(&arguments).map_err(|error| invalid_input(error.0))?;
                self.settled(make).map(Held::Owned)
            }
            ClockClass::Shared { class, .. } => {
                let make = (class.construct)(&arguments).map_err(|error| invalid_input(error.0))?;
                self.settled(make).map(Held::Shared)
            }
        }
    }

    /// A synchronous call inside the runtime, where it can spawn tasks and read the clock, then
    /// the settle step.
    fn settled<R>(&mut self, call: impl FnOnce() -> R) -> Result<R, Ended> {
        let (runtime, idle) = (&self.runtime, &self.idle);
        let (result, duration) = timed(self.file, || {
            runtime.block_on(async {
                let value = call();
                settle(idle).await;
                value
            })
        });
        self.duration += duration;
        result.map_err(Ended::Error)
    }

    /// Awaits `future` on the runtime, then settles; a deadlock names `label`, the operation.
    fn awaited<F: Future>(
        &mut self,
        future: F,
        index: usize,
        label: &str,
    ) -> Result<F::Output, Ended> {
        let (runtime, idle, start) = (&self.runtime, &self.idle, self.start);
        let (result, duration) = timed(self.file, || {
            runtime.block_on(async {
                let value = wait(future, start).await;
                if value.is_some() {
                    settle(idle).await;
                }
                value
            })
        });
        self.duration += duration;
        match result {
            Err(error) => Err(Ended::Error(error)),
            Ok(Some(value)) => Ok(value),
            Ok(None) => {
                let parked_at = lock(&self.idle).parked_at.unwrap_or(self.start);
                let at = millis(parked_at - self.start);
                Err(Ended::Deadlock(format!(
                    "op {index} ({label}): deadlock at {at} ms"
                )))
            }
        }
    }

    fn advance(&mut self, arguments: &[Json]) -> Result<Json, Ended> {
        let ms = match arguments {
            [value] => value
                .as_i64()
                .and_then(|ms| u64::try_from(ms).ok())
                .filter(|ms| *ms > 0),
            _ => None,
        };
        let Some(ms) = ms else {
            return Err(invalid_input(format!(
                "{ADVANCE} takes a positive number of milliseconds"
            )));
        };
        let (runtime, idle) = (&self.runtime, &self.idle);
        let (result, duration) = timed(self.file, || {
            runtime.block_on(async {
                tokio::time::sleep(Duration::from_millis(ms)).await;
                settle(idle).await;
            })
        });
        self.duration += duration;
        result.map(|()| Json::Null).map_err(Ended::Error)
    }

    fn now(&self) -> Json {
        let _context = self.runtime.enter();
        Json::Int(i64::try_from(millis(Instant::now() - self.start)).unwrap_or(i64::MAX))
    }

    fn spawn(
        &mut self,
        class: &ClockClass,
        held: &Held,
        index: usize,
        arguments: &[Json],
    ) -> Result<Json, Ended> {
        let (Some(Json::String(task)), Some(Json::String(method))) =
            (arguments.first(), arguments.get(1))
        else {
            return Err(invalid_input(format!(
                "{SPAWN} takes a task name, a method and its arguments"
            )));
        };
        if self.tasks.contains_key(task) {
            return Err(invalid_input(format!(
                "{SPAWN} of {task}, which is running already"
            )));
        }
        let (ClockClass::Shared { call, .. }, Held::Shared(instance)) = (class, held) else {
            let message = format!("{SPAWN} needs the instance shared, so its methods take &self");
            return Err(invalid_input(message));
        };
        let call = call(method, &Args::Positional(&arguments[2..]))
            .map_err(|error| invalid_input(unknown(error, method, index)))?;
        let future = call(Arc::clone(instance));
        let (runtime, idle) = (&self.runtime, &self.idle);
        // The task's handle, which `@join` awaits later.
        #[allow(clippy::async_yields_async)]
        let (handle, duration) = timed(self.file, || {
            runtime.block_on(async {
                let handle = tokio::spawn(future);
                settle(idle).await;
                handle
            })
        });
        self.duration += duration;
        self.tasks
            .insert(task.clone(), handle.map_err(Ended::Error)?);
        Ok(Json::Null)
    }

    fn join(&mut self, index: usize, arguments: &[Json]) -> Result<Json, Ended> {
        let [Json::String(task)] = arguments else {
            return Err(invalid_input(format!("{JOIN} takes the name of a task")));
        };
        let Some(handle) = self.tasks.remove(task) else {
            return Err(invalid_input(format!(
                "{JOIN} of {task}, which no {SPAWN} started"
            )));
        };
        let label = format!("{JOIN} {task}");
        match self.awaited(handle, index, &label)? {
            Ok(output) => encoded(&*output, index, &label),
            Err(error) => Err(Ended::Error(task_error(error, self.file))),
        }
    }

    fn call(
        &mut self,
        class: &ClockClass,
        held: &mut Held,
        index: usize,
        op: &str,
        arguments: &[Json],
    ) -> Result<Json, Ended> {
        let arguments = Args::Positional(arguments);
        let output: Box<dyn Encode> = match (class, held) {
            (ClockClass::Owned { call, .. }, Held::Owned(instance)) => {
                let call = call(op, &arguments)
                    .map_err(|error| invalid_input(unknown(error, op, index)))?;
                self.awaited(call(&mut **instance), index, op)?
            }
            (ClockClass::Shared { call, .. }, Held::Shared(instance)) => {
                let call = call(op, &arguments)
                    .map_err(|error| invalid_input(unknown(error, op, index)))?;
                self.awaited(call(Arc::clone(instance)), index, op)?
            }
            _ => unreachable!("the constructor of each form makes its form of instance"),
        };
        encoded(&*output, index, op)
    }
}

fn encoded(output: &dyn Encode, index: usize, op: &str) -> Result<Json, Ended> {
    output
        .encode()
        .map_err(|reason| Ended::Invalid(format!("operation {index} ({op}): {reason}")))
}

/// An operation the class does not have names its index, as other class jobs say.
fn unknown(error: InputError, op: &str, index: usize) -> String {
    if error == InputError::unknown_op(op) {
        format!("unknown operation \"{op}\" at index {index}")
    } else {
        error.0
    }
}

/// A spawned task's panic, as a call's panic reads: its message, and the trace the panic hook
/// recorded on this thread when it is that panic's.
fn task_error(error: JoinError, file: &str) -> UserError {
    match error.try_into_panic() {
        Ok(payload) => {
            let message = panic_text(&*payload);
            let mut recorded = take_panic(file);
            if recorded.message != message {
                recorded = UserError::new(&recorded.error_type, message);
            }
            recorded
        }
        Err(_) => UserError::new("Cancelled", "the task was cancelled"),
    }
}

/// Drops what the case left: its tasks' handles and the instance inside the runtime, which some
/// of their drops need, then the runtime and every task still pending. A panic in a drop is the
/// case's no longer.
fn end(runtime: Runtime, tasks: HashMap<String, JoinHandle<SendOutput>>, held: Option<Held>) {
    let _ = panic::catch_unwind(AssertUnwindSafe(|| {
        let _context = runtime.enter();
        drop(tasks);
        drop(held);
    }));
    let _ = panic::catch_unwind(AssertUnwindSafe(|| drop(runtime)));
}

#[cfg(test)]
mod tests {
    use std::collections::VecDeque;
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::{Arc, Mutex};
    use std::time::Duration;

    use tokio::sync::Notify;
    use tokio::time::Instant;

    use super::{block_on, owned_call, run, sendable, shared_call, ClockClass, OwnedCall};
    use super::{SharedCall, Status};
    use crate::events::Outcome;
    use crate::json::Json;
    use crate::{Args, Concurrent, Construct, InputError, SharedConstruct, SharedMethod};

    const FILE: &str = "/ws/projects/timer/";

    /// Owned: methods take `&mut self`.
    struct Timer {
        start: Instant,
        fired: Arc<Mutex<Vec<i64>>>,
    }

    impl Timer {
        fn elapsed(start: Instant) -> i64 {
            start.elapsed().as_millis() as i64
        }

        async fn sleep(&mut self, ms: i64) -> i64 {
            let before = Instant::now();
            tokio::time::sleep(Duration::from_millis(ms as u64)).await;
            Timer::elapsed(before)
        }

        async fn hold(&mut self) -> i64 {
            std::future::pending::<()>().await;
            0
        }

        fn later(&mut self, ms: i64) {
            let (start, fired) = (self.start, Arc::clone(&self.fired));
            tokio::spawn(async move {
                tokio::time::sleep(Duration::from_millis(ms as u64)).await;
                fired.lock().unwrap().push(Timer::elapsed(start));
            });
        }

        fn fired(&mut self) -> Vec<i64> {
            self.fired.lock().unwrap().clone()
        }
    }

    fn timer_construct(_: &Args) -> Result<Construct, InputError> {
        Ok(Box::new(|| {
            let timer = Timer {
                start: Instant::now(),
                fired: Arc::default(),
            };
            crate::object(timer)
        }))
    }

    fn timer_call(op: &str, args: &Args) -> Result<OwnedCall, InputError> {
        let ms: i64 = if matches!(op, "sleep" | "later") {
            args.at(0, "ms")?
        } else {
            0
        };
        let call = match op {
            "sleep" => owned_call(move |object| {
                Box::pin(
                    async move { crate::output(crate::instance::<Timer>(object).sleep(ms).await) },
                )
            }),
            "hold" => owned_call(move |object| {
                Box::pin(
                    async move { crate::output(crate::instance::<Timer>(object).hold().await) },
                )
            }),
            "later" => owned_call(move |object| {
                Box::pin(async move {
                    crate::instance::<Timer>(object).later(ms);
                    crate::output(())
                })
            }),
            "fired" => owned_call(move |object| {
                Box::pin(async move { crate::output(crate::instance::<Timer>(object).fired()) })
            }),
            _ => return Err(InputError::unknown_op(op)),
        };
        Ok(call)
    }

    const TIMER: ClockClass = ClockClass::Owned {
        name: "Timer",
        construct: timer_construct,
        call: timer_call,
    };

    static DROPPED: AtomicBool = AtomicBool::new(false);

    /// Shared: methods take `&self`, and tasks call them.
    #[derive(Default)]
    struct Mailbox {
        messages: Mutex<VecDeque<String>>,
        arrived: Notify,
    }

    impl Mailbox {
        fn put(&self, body: String) -> i64 {
            let mut messages = self.messages.lock().unwrap();
            messages.push_back(body);
            self.arrived.notify_one();
            messages.len() as i64
        }

        async fn take(&self) -> String {
            loop {
                let arrived = self.arrived.notified();
                if let Some(body) = self.messages.lock().unwrap().pop_front() {
                    return body;
                }
                arrived.await;
            }
        }

        async fn boom(&self) -> String {
            tokio::time::sleep(Duration::from_millis(5)).await;
            panic!("boom");
        }

        async fn linger(&self) -> String {
            struct Flag;
            impl Drop for Flag {
                fn drop(&mut self) {
                    DROPPED.store(true, Ordering::SeqCst);
                }
            }
            let _flag = Flag;
            std::future::pending::<String>().await
        }
    }

    fn mailbox_construct(_: &Args) -> Result<SharedConstruct, InputError> {
        Ok(Box::new(|| crate::shared(Mailbox::default())))
    }

    fn mailbox_method(op: &str, _: &Args) -> Result<SharedMethod, InputError> {
        Err(InputError::unknown_op(op))
    }

    fn mailbox_call(op: &str, args: &Args) -> Result<SharedCall, InputError> {
        let call = match op {
            "put" => {
                let body: String = args.at(0, "body")?;
                shared_call(move |object| async move {
                    sendable(crate::shared_instance::<Mailbox>(&*object).put(body))
                })
            }
            "take" => shared_call(move |object| async move {
                sendable(crate::shared_instance::<Mailbox>(&*object).take().await)
            }),
            "boom" => shared_call(move |object| async move {
                sendable(crate::shared_instance::<Mailbox>(&*object).boom().await)
            }),
            "linger" => shared_call(move |object| async move {
                sendable(crate::shared_instance::<Mailbox>(&*object).linger().await)
            }),
            _ => return Err(InputError::unknown_op(op)),
        };
        Ok(call)
    }

    const MAILBOX: ClockClass = ClockClass::Shared {
        class: Concurrent {
            name: "Mailbox",
            construct: mailbox_construct,
            method: mailbox_method,
        },
        call: mailbox_call,
    };

    fn case(class: &ClockClass, steps: &[(&str, &str)]) -> Outcome {
        let ops: Vec<String> = steps.iter().map(|(op, _)| op.to_string()).collect();
        let args: Vec<Vec<Json>> = steps
            .iter()
            .map(|(_, args)| match Json::parse(args) {
                Ok(Json::Array(values)) => values,
                _ => panic!("arguments must be a JSON array: {args}"),
            })
            .collect();
        run(FILE, class, &ops, &args)
    }

    fn outputs(outcome: Outcome) -> String {
        match outcome.status {
            Status::Ok(output) => output.text(),
            other => panic!("expected outputs, got {other:?}"),
        }
    }

    #[test]
    fn advance_fires_each_timer_at_its_own_time_and_now_reads_the_virtual_time() {
        let outcome = case(
            &TIMER,
            &[
                ("Timer", "[]"),
                ("later", "[25]"),
                ("later", "[10]"),
                ("@advance", "[30]"),
                ("fired", "[]"),
                ("@now", "[]"),
            ],
        );
        assert_eq!(outputs(outcome), "[null,null,null,null,[10,25],30]");
    }

    #[test]
    fn an_async_method_is_awaited_while_the_clock_moves() {
        let outcome = case(
            &TIMER,
            &[
                ("Timer", "[]"),
                ("@now", "[]"),
                ("sleep", "[1500]"),
                ("@now", "[]"),
            ],
        );
        assert_eq!(outputs(outcome), "[null,0,1500,1500]");
    }

    #[test]
    fn a_wait_that_nothing_can_end_is_a_deadlock_at_the_virtual_time_it_began() {
        let outcome = case(
            &TIMER,
            &[("Timer", "[]"), ("@advance", "[2000]"), ("hold", "[]")],
        );
        let Status::Deadlocked { reason, op } = outcome.status else {
            panic!("expected a deadlock, got {:?}", outcome.status);
        };
        assert_eq!(reason, "op 2 (hold): deadlock at 2000 ms");
        assert_eq!(op, (2, vec![Json::Null, Json::Null]));
    }

    #[test]
    fn a_spawned_call_waits_as_a_task_until_its_join() {
        let outcome = case(
            &MAILBOX,
            &[
                ("Mailbox", "[]"),
                ("@spawn", r#"["r1", "take"]"#),
                ("@advance", "[1000]"),
                ("put", r#"["a"]"#),
                ("@join", r#"["r1"]"#),
                ("@now", "[]"),
            ],
        );
        assert_eq!(outputs(outcome), r#"[null,null,null,1,"a",1000]"#);
    }

    #[test]
    fn a_join_that_nothing_can_end_is_a_deadlock() {
        let outcome = case(
            &MAILBOX,
            &[
                ("Mailbox", "[]"),
                ("@spawn", r#"["r1", "take"]"#),
                ("@join", r#"["r1"]"#),
            ],
        );
        let Status::Deadlocked { reason, .. } = outcome.status else {
            panic!("expected a deadlock, got {:?}", outcome.status);
        };
        assert_eq!(reason, "op 2 (@join r1): deadlock at 0 ms");
    }

    #[test]
    fn a_spawned_tasks_panic_is_the_error_of_its_join() {
        crate::harness::install_panic_hook();
        let outcome = case(
            &MAILBOX,
            &[
                ("Mailbox", "[]"),
                ("@spawn", r#"["r1", "boom"]"#),
                ("@advance", "[10]"),
                ("@join", r#"["r1"]"#),
            ],
        );
        let Status::Error { error, op } = outcome.status else {
            panic!("expected an error, got {:?}", outcome.status);
        };
        assert_eq!(
            (error.message.as_str(), op.map(|(index, _)| index)),
            ("boom", Some(3))
        );
    }

    #[test]
    fn a_task_still_pending_when_the_case_ends_is_dropped() {
        DROPPED.store(false, Ordering::SeqCst);
        let outcome = case(
            &MAILBOX,
            &[
                ("Mailbox", "[]"),
                ("@spawn", r#"["r1", "linger"]"#),
                ("put", r#"["a"]"#),
            ],
        );
        assert_eq!(outputs(outcome), "[null,null,1]");
        assert!(DROPPED.load(Ordering::SeqCst));
    }

    #[test]
    fn spawn_needs_the_shared_instance() {
        let outcome = case(
            &TIMER,
            &[("Timer", "[]"), ("@spawn", r#"["r1", "sleep", 5]"#)],
        );
        let Status::Error { error, .. } = outcome.status else {
            panic!("expected an error, got {:?}", outcome.status);
        };
        assert!(error.message.contains("&self"), "{}", error.message);
    }

    #[test]
    fn an_unknown_operation_names_its_index() {
        let outcome = case(&TIMER, &[("Timer", "[]"), ("@now", "[]"), ("nope", "[]")]);
        let Status::Error { error, .. } = outcome.status else {
            panic!("expected an error, got {:?}", outcome.status);
        };
        assert_eq!(error.message, "unknown operation \"nope\" at index 2");
    }

    #[test]
    fn a_stress_worker_runs_an_async_call_on_the_real_clock() {
        let started = std::time::Instant::now();
        let waited = std::thread::spawn(|| {
            block_on(async {
                tokio::time::sleep(Duration::from_millis(5)).await;
                7
            })
        });
        assert_eq!(waited.join().unwrap(), 7);
        assert!(started.elapsed() >= Duration::from_millis(5));
    }
}
