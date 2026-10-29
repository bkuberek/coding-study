//! One stress run of a concurrent job (docs/specs/runners.md#run-procedure).
//!
//! Every run is independent: fresh argument decoding, a fresh instance, fresh probe sections and
//! fresh PRNGs. Setup runs on the case thread; the workers are threads that wait at a start gate
//! and are released together; the coordinator waits until every worker finished, one failed, or
//! the deadline passed, then runs the final script. A thread cannot be stopped from outside:
//! after a failure or a stall the workers stop at their next op boundary, a worker stuck in user
//! code keeps running, and the runner asks for a restart when one still runs shortly after.

use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Barrier, Condvar, Mutex, MutexGuard, PoisonError};
use std::thread;
use std::time::{Duration, Instant};

use crate::capture;
use crate::events::{Outcome, UserError};
use crate::harness::{elapsed_ns, timed};
use crate::json::Json;
use crate::request::{Script, StressCase};
use crate::{Args, Concurrent, InputError, Instance, SharedConstruct, SharedMethod};

const SETUP: &str = "setup";
const WORKER: &str = "worker";
const FINAL: &str = "final";
const HARNESS_PREFIX: char = '@';
const HARNESS_ERROR: &str = "HarnessError";
const PRNG_MULTIPLIER: i64 = 1_000_003;
/// How long the workers of a finished run get to return.
const LEFTOVER_GRACE: Duration = Duration::from_millis(200);
const WORKER_STACK_BYTES: usize = 16 * 1024 * 1024;
const CONSTRUCTOR_OP: usize = 0;

/// Runs one stress case with what its code prints captured: one buffer for the run, shared by
/// every worker.
pub fn run(file: &str, class: &Concurrent, case: &StressCase) -> (Outcome, Workers) {
    let output = capture::start();
    let (mut outcome, workers) = Run::new(file, case).run(class);
    outcome.stdout = capture::stop(output);
    (outcome, workers)
}

/// The worker threads of a run, which may outlive it after a failure or a stall.
pub struct Workers {
    shared: Arc<Shared>,
    started: usize,
}

impl Workers {
    /// The worker threads still running after a short grace period.
    pub fn still_running(&self) -> usize {
        let deadline = Instant::now() + LEFTOVER_GRACE;
        let mut state = self.shared.lock();
        while state.exited < self.started {
            let now = Instant::now();
            if now >= deadline {
                break;
            }
            state = self.shared.wait(state, deadline - now);
        }
        self.started - state.exited
    }
}

/// One decoded op: a method call, or a harness op.
enum Op {
    Call(SharedMethod),
    Harness { name: String, args: Vec<Json> },
}

/// Why an op failed: a panic or a harness error, or a result that cannot be encoded.
enum Fault {
    Raised(UserError),
    Invalid(String),
}

impl Fault {
    fn input(error: InputError) -> Self {
        Fault::Raised(UserError::invalid_input(error.0))
    }

    fn at(self, phase: &'static str, op_index: usize, worker: Option<usize>) -> Failure {
        Failure {
            fault: self,
            phase,
            op_index,
            worker,
        }
    }
}

/// A failed op and where it failed.
struct Failure {
    fault: Fault,
    phase: &'static str,
    op_index: usize,
    worker: Option<usize>,
}

impl Failure {
    /// The run's case result; `progress` lists the unfinished workers of a worker failure.
    fn outcome(self, duration_ns: u64, progress: Vec<Json>) -> Outcome {
        let mut outcome = match self.fault {
            Fault::Raised(error) => Outcome::raised(error, duration_ns),
            Fault::Invalid(reason) => Outcome::invalid(reason, duration_ns),
        };
        outcome.stress = vec![
            ("phase", Json::String(self.phase.to_string())),
            ("op_index", count(self.op_index)),
        ];
        if let Some(worker) = self.worker {
            outcome.stress.push(("worker", count(worker)));
            outcome.stress.push(("progress", Json::Array(progress)));
        }
        outcome
    }
}

fn count(value: usize) -> Json {
    Json::Int(i64::try_from(value).unwrap_or(i64::MAX))
}

/// Step 1: every argument of setup, workers and final decoded before anything runs.
struct Plan {
    construct: SharedConstruct,
    setup: Vec<Op>,
    workers: Vec<Vec<Op>>,
    final_ops: Vec<Op>,
}

impl Plan {
    fn decode(class: &Concurrent, case: &StressCase) -> Result<Plan, Failure> {
        let setup = &case.setup;
        lengths(setup, SETUP, None)?;
        let first = &setup.ops[CONSTRUCTOR_OP];
        if first != class.name {
            let message = format!("operation 0 must be \"{}\", got \"{first}\"", class.name);
            return Err(Fault::input(InputError(message)).at(SETUP, CONSTRUCTOR_OP, None));
        }
        let construct = (class.construct)(&Args::Positional(&setup.args[CONSTRUCTOR_OP]))
            .map_err(|error| Fault::input(error).at(SETUP, CONSTRUCTOR_OP, None))?;
        let after_constructor = CONSTRUCTOR_OP + 1;
        let setup_ops = ops(class, setup, after_constructor, SETUP, None)?;
        let workers = case
            .workers
            .iter()
            .enumerate()
            .map(|(ordinal, script)| {
                lengths(script, WORKER, Some(ordinal))?;
                ops(class, script, 0, WORKER, Some(ordinal))
            })
            .collect::<Result<_, _>>()?;
        let final_ops = match &case.final_script {
            Some(script) => {
                lengths(script, FINAL, None)?;
                ops(class, script, 0, FINAL, None)?
            }
            None => Vec::new(),
        };
        Ok(Plan {
            construct,
            setup: setup_ops,
            workers,
            final_ops,
        })
    }
}

fn lengths(script: &Script, phase: &'static str, worker: Option<usize>) -> Result<(), Failure> {
    if script.ops.len() == script.args.len() {
        return Ok(());
    }
    let message = format!(
        "{} operations but {} argument lists",
        script.ops.len(),
        script.args.len()
    );
    Err(Fault::input(InputError(message)).at(phase, 0, worker))
}

/// The ops of a script from index `first`; a harness op keeps its arguments as they are.
fn ops(
    class: &Concurrent,
    script: &Script,
    first: usize,
    phase: &'static str,
    worker: Option<usize>,
) -> Result<Vec<Op>, Failure> {
    let indexed = script.ops.iter().zip(&script.args).enumerate().skip(first);
    indexed
        .map(|(index, (name, args))| {
            if name.starts_with(HARNESS_PREFIX) {
                return Ok(Op::Harness {
                    name: name.clone(),
                    args: args.clone(),
                });
            }
            (class.method)(name, &Args::Positional(args))
                .map(Op::Call)
                .map_err(|error| Fault::input(error).at(phase, index, worker))
        })
        .collect()
}

/// What the workers and the coordinator share.
struct Shared {
    state: Mutex<State>,
    changed: Condvar,
    stopped: AtomicBool,
    completed: Vec<AtomicUsize>,
    in_op: Vec<AtomicBool>,
    sections: Sections,
}

struct State {
    /// A worker's outputs, once it finished.
    outputs: Vec<Option<Vec<Json>>>,
    finished: usize,
    failure: Option<Failure>,
    /// Worker threads that returned, however they returned.
    exited: usize,
}

impl Shared {
    fn lock(&self) -> MutexGuard<'_, State> {
        self.state.lock().unwrap_or_else(PoisonError::into_inner)
    }

    fn wait<'a>(&self, state: MutexGuard<'a, State>, timeout: Duration) -> MutexGuard<'a, State> {
        self.changed
            .wait_timeout(state, timeout)
            .unwrap_or_else(PoisonError::into_inner)
            .0
    }

    fn finish(&self, worker: usize, outputs: Vec<Json>) {
        let mut state = self.lock();
        state.outputs[worker] = Some(outputs);
        state.finished += 1;
        self.changed.notify_all();
    }

    /// Records the first failure; one reported after the coordinator decided is dropped.
    fn fail(&self, failure: Failure) {
        let mut state = self.lock();
        if state.failure.is_none() && !self.stopped.load(Ordering::SeqCst) {
            state.failure = Some(failure);
        }
        self.changed.notify_all();
    }

    /// The progress of every worker that did not finish, the failing one included.
    fn unfinished(&self) -> Vec<Json> {
        let state = self.lock();
        let unfinished = state.outputs.iter().enumerate();
        unfinished
            .filter(|(_, outputs)| outputs.is_none())
            .map(|(worker, _)| {
                Json::Object(vec![
                    ("worker".to_string(), count(worker)),
                    (
                        "completed".to_string(),
                        count(self.completed[worker].load(Ordering::SeqCst)),
                    ),
                    (
                        "in_op".to_string(),
                        Json::Bool(self.in_op[worker].load(Ordering::SeqCst)),
                    ),
                ])
            })
            .collect()
    }
}

/// Counts a worker thread as exited when it returns, a panic included.
struct Exit<'a>(&'a Shared);

impl Drop for Exit<'_> {
    fn drop(&mut self) {
        self.0.lock().exited += 1;
        self.0.changed.notify_all();
    }
}

struct Run<'a> {
    file: &'a str,
    case: &'a StressCase,
    shared: Arc<Shared>,
}

impl<'a> Run<'a> {
    fn new(file: &'a str, case: &'a StressCase) -> Self {
        let workers = case.workers.len();
        let shared = Shared {
            state: Mutex::new(State {
                outputs: (0..workers).map(|_| None).collect(),
                finished: 0,
                failure: None,
                exited: 0,
            }),
            changed: Condvar::new(),
            stopped: AtomicBool::new(false),
            completed: (0..workers).map(|_| AtomicUsize::new(0)).collect(),
            in_op: (0..workers).map(|_| AtomicBool::new(false)).collect(),
            sections: Sections::default(),
        };
        Run {
            file,
            case,
            shared: Arc::new(shared),
        }
    }

    fn run(self, class: &Concurrent) -> (Outcome, Workers) {
        let none = Workers {
            shared: Arc::clone(&self.shared),
            started: 0,
        };
        let plan = match Plan::decode(class, self.case) {
            Ok(plan) => plan,
            Err(failure) => return (failure.outcome(0, Vec::new()), none),
        };
        let (instance, setup) = match self.setup(plan.construct, plan.setup) {
            Ok(done) => done,
            Err(failure) => return (failure.outcome(0, Vec::new()), none),
        };
        let started_workers = plan.workers.len();
        let started = self.start(plan.workers, &instance);
        let (failure, all_finished) = self.decide(started, started_workers);
        let duration = elapsed_ns(started);
        let workers = Workers {
            shared: Arc::clone(&self.shared),
            started: started_workers,
        };
        if let Some(failure) = failure {
            return (failure.outcome(duration, self.shared.unfinished()), workers);
        }
        if !all_finished {
            let mut outcome = Outcome::stalled(duration);
            outcome.stress = vec![("progress", Json::Array(self.shared.unfinished()))];
            return (outcome, workers);
        }
        let final_outputs = match self.sequence(&instance, plan.final_ops, 0, FINAL) {
            Ok(outputs) => outputs,
            Err(failure) => return (failure.outcome(duration, Vec::new()), workers),
        };
        let outputs = self.shared.lock().outputs.drain(..).collect::<Vec<_>>();
        let output = Json::Object(vec![
            ("setup".to_string(), Json::Array(setup)),
            (
                "workers".to_string(),
                Json::Array(
                    outputs
                        .into_iter()
                        .map(|worker| Json::Array(worker.unwrap_or_default()))
                        .collect(),
                ),
            ),
            ("final".to_string(), Json::Array(final_outputs)),
        ]);
        let mut outcome = Outcome::returned(output, duration);
        outcome.stress = vec![("sections", self.shared.sections.snapshot())];
        (outcome, workers)
    }

    /// Constructs the instance and runs the rest of the setup on the case thread.
    fn setup(
        &self,
        construct: SharedConstruct,
        ops: Vec<Op>,
    ) -> Result<(Instance, Vec<Json>), Failure> {
        let (instance, _) = timed(self.file, construct);
        let instance =
            instance.map_err(|error| Fault::Raised(error).at(SETUP, CONSTRUCTOR_OP, None))?;
        let mut outputs = vec![Json::Null];
        outputs.extend(self.sequence(&instance, ops, CONSTRUCTOR_OP + 1, SETUP)?);
        Ok((instance, outputs))
    }

    /// Runs ops on the case thread, numbered from `first`.
    fn sequence(
        &self,
        instance: &Instance,
        ops: Vec<Op>,
        first: usize,
        phase: &'static str,
    ) -> Result<Vec<Json>, Failure> {
        let mut harness = Harness::new(&self.shared.sections);
        ops.into_iter()
            .enumerate()
            .map(|(index, op)| {
                execute(op, instance, &mut harness, self.file)
                    .map_err(|fault| fault.at(phase, first + index, None))
            })
            .collect()
    }

    /// Starts one thread per worker, waits until each waits at the gate, and opens it; the
    /// run's clock starts then.
    fn start(&self, workers: Vec<Vec<Op>>, instance: &Instance) -> Instant {
        let gate = Arc::new(Barrier::new(workers.len() + 1));
        for (ordinal, ops) in workers.into_iter().enumerate() {
            let worker = Worker {
                ordinal,
                ops,
                shared: Arc::clone(&self.shared),
                instance: Arc::clone(instance),
                gate: Arc::clone(&gate),
                file: self.file.to_string(),
                random: Random::new(self.case.seed, ordinal),
                yield_probability: self.case.yield_probability,
                max_yields: self.case.max_yields,
            };
            thread::Builder::new()
                .name(format!("cs-worker-{ordinal}"))
                .stack_size(WORKER_STACK_BYTES)
                .spawn(move || worker.run())
                .expect("cannot start a worker thread");
        }
        gate.wait();
        Instant::now()
    }

    /// Waits until every worker finished, one failed, or the deadline passed, then stops the
    /// workers: the first failure, and whether all finished.
    fn decide(&self, started: Instant, workers: usize) -> (Option<Failure>, bool) {
        let deadline = started + Duration::from_millis(self.case.deadline_ms);
        let mut state = self.shared.lock();
        while state.failure.is_none() && state.finished < workers {
            let now = Instant::now();
            if now >= deadline {
                break;
            }
            state = self.shared.wait(state, deadline - now);
        }
        self.shared.stopped.store(true, Ordering::SeqCst);
        (state.failure.take(), state.finished == workers)
    }
}

struct Worker {
    ordinal: usize,
    ops: Vec<Op>,
    shared: Arc<Shared>,
    instance: Instance,
    gate: Arc<Barrier>,
    file: String,
    random: Random,
    yield_probability: f64,
    max_yields: u64,
}

impl Worker {
    fn run(mut self) {
        let shared = Arc::clone(&self.shared);
        let _exit = Exit(&shared);
        let mut harness = Harness::new(&shared.sections);
        let ordinal = self.ordinal;
        self.gate.wait();
        let mut outputs = Vec::with_capacity(self.ops.len());
        for (index, op) in std::mem::take(&mut self.ops).into_iter().enumerate() {
            if shared.stopped.load(Ordering::SeqCst) {
                return;
            }
            if self.random.unit() < self.yield_probability {
                yield_times(1 + self.random.below(self.max_yields));
            }
            shared.in_op[ordinal].store(true, Ordering::SeqCst);
            match execute(op, &self.instance, &mut harness, &self.file) {
                Ok(value) => outputs.push(value),
                Err(fault) => {
                    shared.fail(fault.at(WORKER, index, Some(ordinal)));
                    return;
                }
            }
            shared.completed[ordinal].store(index + 1, Ordering::SeqCst);
            shared.in_op[ordinal].store(false, Ordering::SeqCst);
        }
        shared.finish(ordinal, outputs);
    }
}

/// Runs one op and encodes its result at once; a harness op has no result.
fn execute(op: Op, instance: &Instance, harness: &mut Harness, file: &str) -> Result<Json, Fault> {
    match op {
        Op::Harness { name, args } => harness
            .run(&name, &args)
            .map(|()| Json::Null)
            .map_err(|message| Fault::Raised(UserError::new(HARNESS_ERROR, message))),
        Op::Call(call) => {
            let (result, _) = timed(file, || call(&**instance));
            result
                .map_err(Fault::Raised)?
                .encode()
                .map_err(Fault::Invalid)
        }
    }
}

fn yield_times(count: u64) {
    for _ in 0..count {
        thread::yield_now();
    }
}

/// A worker's PRNG, SplitMix64: only perturbation draws from it, so its stream need not match
/// the other runtimes'.
struct Random(u64);

impl Random {
    fn new(seed: i64, ordinal: usize) -> Self {
        let ordinal = i64::try_from(ordinal).unwrap_or(i64::MAX);
        Random(seed.wrapping_mul(PRNG_MULTIPLIER).wrapping_add(ordinal) as u64)
    }

    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut mixed = self.0;
        mixed = (mixed ^ (mixed >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        mixed = (mixed ^ (mixed >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        mixed ^ (mixed >> 31)
    }

    /// Uniform in [0, 1).
    fn unit(&mut self) -> f64 {
        (self.next() >> 11) as f64 / (1_u64 << 53) as f64
    }

    /// Uniform in [0, bound).
    fn below(&mut self, bound: u64) -> u64 {
        self.next() % bound.max(1)
    }
}

const ENTER: &str = "@enter";
const EXIT: &str = "@exit";
const PAUSE: &str = "@pause";
const EXCLUSIVE: &str = "exclusive";
const SHARED: &str = "shared";

/// One run's probe sections, created on first use, in the order of first use
/// (docs/specs/runners.md#harness-ops).
#[derive(Default)]
struct Sections(Mutex<Vec<(String, Section)>>);

#[derive(Default)]
struct Section {
    shared: i64,
    exclusive: i64,
    entries: i64,
    violations: i64,
    max_occupancy: i64,
}

impl Sections {
    fn update(&self, name: &str, change: impl FnOnce(&mut Section)) {
        let mut sections = self.0.lock().unwrap_or_else(PoisonError::into_inner);
        let index = match sections.iter().position(|(known, _)| known == name) {
            Some(index) => index,
            None => {
                sections.push((name.to_string(), Section::default()));
                sections.len() - 1
            }
        };
        change(&mut sections[index].1);
    }

    fn enter(&self, name: &str, exclusive: bool) {
        self.update(name, |section| {
            let violated = if exclusive {
                section.shared + section.exclusive > 0
            } else {
                section.exclusive > 0
            };
            section.violations += i64::from(violated);
            if exclusive {
                section.exclusive += 1;
            } else {
                section.shared += 1;
            }
            section.entries += 1;
            section.max_occupancy = section
                .max_occupancy
                .max(section.shared + section.exclusive);
        });
    }

    fn exit(&self, name: &str, exclusive: bool) {
        self.update(name, |section| {
            if exclusive {
                section.exclusive -= 1;
            } else {
                section.shared -= 1;
            }
        });
    }

    fn snapshot(&self) -> Json {
        let sections = self.0.lock().unwrap_or_else(PoisonError::into_inner);
        Json::Object(
            sections
                .iter()
                .map(|(name, section)| {
                    let counts = vec![
                        ("entries".to_string(), Json::Int(section.entries)),
                        ("violations".to_string(), Json::Int(section.violations)),
                        (
                            "max_occupancy".to_string(),
                            Json::Int(section.max_occupancy),
                        ),
                    ];
                    (name.clone(), Json::Object(counts))
                })
                .collect(),
        )
    }
}

/// One worker's harness ops: the sections it is inside, with the mode it entered each with, last
/// entered last.
struct Harness<'a> {
    sections: &'a Sections,
    entered: Vec<(String, bool)>,
}

impl<'a> Harness<'a> {
    fn new(sections: &'a Sections) -> Self {
        Harness {
            sections,
            entered: Vec::new(),
        }
    }

    fn run(&mut self, op: &str, args: &[Json]) -> Result<(), String> {
        match (op, args) {
            (ENTER, [Json::String(name), Json::String(mode)])
                if mode == EXCLUSIVE || mode == SHARED =>
            {
                let exclusive = mode == EXCLUSIVE;
                self.sections.enter(name, exclusive);
                self.entered.push((name.clone(), exclusive));
                Ok(())
            }
            (EXIT, [Json::String(name)]) => {
                let Some(index) = self.entered.iter().rposition(|(known, _)| known == name) else {
                    return Err(format!("{EXIT} \"{name}\" without a matching {ENTER}"));
                };
                let (_, exclusive) = self.entered.remove(index);
                self.sections.exit(name, exclusive);
                Ok(())
            }
            (PAUSE, [count]) if count.as_i64().is_some() => {
                yield_times(count.as_i64().unwrap_or(0).max(0) as u64);
                Ok(())
            }
            _ => Err(format!(
                "{op} cannot take {}",
                Json::Array(args.to_vec()).text()
            )),
        }
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Mutex;

    use super::{Run, Workers};
    use crate::events::{Outcome, Status};
    use crate::json::Json;
    use crate::request::{Script, StressCase};
    use crate::{Args, Concurrent, InputError, SharedConstruct, SharedMethod};

    struct Tally {
        count: Mutex<i32>,
    }

    fn construct(args: &Args) -> Result<SharedConstruct, InputError> {
        args.count(0, "Tally")?;
        Ok(Box::new(|| {
            crate::shared(Tally {
                count: Mutex::new(0),
            })
        }))
    }

    fn method(op: &str, args: &Args) -> Result<SharedMethod, InputError> {
        match op {
            "increment" => {
                args.count(0, op)?;
                Ok(Box::new(|object| {
                    let tally = crate::shared_instance::<Tally>(object);
                    let mut count = tally.count.lock().unwrap();
                    *count += 1;
                    crate::output(*count)
                }))
            }
            "step" => {
                args.count(1, op)?;
                let index: i32 = args.at(0, "index")?;
                Ok(Box::new(move |_| {
                    if index == 100 {
                        panic!("failed at {index}");
                    }
                    crate::output(index)
                }))
            }
            "wait" => {
                args.count(0, op)?;
                Ok(Box::new(|_| loop {
                    std::thread::park();
                }))
            }
            _ => Err(InputError::unknown_op(op)),
        }
    }

    const TALLY: Concurrent = Concurrent {
        name: "Tally",
        construct,
        method,
    };

    fn script(ops: &[&str], args: &[Json]) -> Script {
        Script {
            ops: ops.iter().map(|op| op.to_string()).collect(),
            args: args
                .iter()
                .map(|arguments| arguments.as_array().unwrap_or_default().to_vec())
                .collect(),
        }
    }

    fn repeated(op: &str, times: usize) -> Script {
        script(&vec![op; times], &vec![Json::Array(Vec::new()); times])
    }

    fn steps(count: i64) -> Script {
        let args: Vec<Json> = (0..count)
            .map(|index| Json::Array(vec![Json::Int(index)]))
            .collect();
        script(&vec!["step"; args.len()], &args)
    }

    fn case(setup: Script, workers: Vec<Script>, final_script: Option<Script>) -> StressCase {
        StressCase {
            seed: 7,
            deadline_ms: 5000,
            yield_probability: 0.5,
            max_yields: 3,
            setup,
            workers,
            final_script,
        }
    }

    fn tally() -> Script {
        repeated("Tally", 1)
    }

    fn run(case: &StressCase) -> (Outcome, Workers) {
        crate::harness::install_panic_hook();
        Run::new("/ws/rust/practice/tally.rs", case).run(&TALLY)
    }

    fn field<'a>(outcome: &'a Outcome, key: &str) -> Option<&'a Json> {
        outcome
            .stress
            .iter()
            .find(|(name, _)| *name == key)
            .map(|(_, value)| value)
    }

    fn error(outcome: &Outcome) -> (&str, &str) {
        match &outcome.status {
            Status::Error { error, .. } => (&error.error_type, &error.message),
            other => panic!("not an error: {other:?}"),
        }
    }

    #[test]
    fn a_completed_run_reports_every_output_and_its_sections() {
        let increments = repeated("increment", 50);
        let workers = vec![increments; 4];
        let case = case(tally(), workers, Some(repeated("increment", 1)));
        let (outcome, workers) = run(&case);
        let Status::Ok(output) = &outcome.status else {
            panic!("not ok: {outcome:?}");
        };
        let mut values: Vec<i64> = output
            .get("workers")
            .unwrap()
            .as_array()
            .unwrap()
            .iter()
            .flat_map(|worker| worker.as_array().unwrap().iter().filter_map(Json::as_i64))
            .collect();
        values.sort_unstable();
        values.dedup();
        assert_eq!(values.len(), 200);
        assert_eq!(output.get("setup").unwrap().text(), "[null]");
        assert_eq!(output.get("final").unwrap().text(), "[201]");
        assert_eq!(field(&outcome, "sections").unwrap().text(), "{}");
        assert_eq!(workers.still_running(), 0);
    }

    #[test]
    fn probe_sections_count_overlapping_entries() {
        let setup = script(
            &["Tally", "@enter", "@enter", "@pause", "@exit", "@exit"],
            &[
                Json::Array(vec![]),
                Json::parse(r#"["data", "exclusive"]"#).unwrap(),
                Json::parse(r#"["data", "shared"]"#).unwrap(),
                Json::parse("[2]").unwrap(),
                Json::parse(r#"["data"]"#).unwrap(),
                Json::parse(r#"["data"]"#).unwrap(),
            ],
        );
        let probe = script(
            &["@enter", "@exit"],
            &[
                Json::parse(r#"["data", "shared"]"#).unwrap(),
                Json::parse(r#"["data"]"#).unwrap(),
            ],
        );
        let (outcome, _) = run(&case(setup, vec![probe.clone(), probe], None));
        let sections = field(&outcome, "sections").unwrap().get("data").unwrap();
        assert_eq!(sections.get("entries").unwrap().as_i64(), Some(4));
        assert_eq!(sections.get("violations").unwrap().as_i64(), Some(1));
        assert!(sections.get("max_occupancy").unwrap().as_i64().unwrap() >= 2);
    }

    #[test]
    fn an_exit_without_enter_is_a_harness_error() {
        let exit = script(&["@exit"], &[Json::parse(r#"["data"]"#).unwrap()]);
        let (outcome, _) = run(&case(tally(), vec![exit, repeated("increment", 1)], None));
        assert_eq!(
            error(&outcome),
            ("HarnessError", "@exit \"data\" without a matching @enter")
        );
        assert_eq!(field(&outcome, "phase").unwrap().text(), "\"worker\"");
        assert_eq!(field(&outcome, "worker").unwrap().as_i64(), Some(0));
    }

    #[test]
    fn a_worker_panic_names_its_phase_worker_and_op() {
        let (outcome, workers) = run(&case(tally(), vec![steps(200), steps(200)], None));
        assert_eq!(error(&outcome), ("panic", "failed at 100"));
        assert_eq!(field(&outcome, "op_index").unwrap().as_i64(), Some(100));
        let failing = field(&outcome, "worker").unwrap().as_i64().unwrap();
        let progress = field(&outcome, "progress").unwrap().as_array().unwrap();
        let listed = progress
            .iter()
            .find(|item| item.get("worker").and_then(Json::as_i64) == Some(failing))
            .unwrap();
        assert_eq!(
            listed.text(),
            format!(r#"{{"worker":{failing},"completed":100,"in_op":true}}"#)
        );
        assert_eq!(workers.still_running(), 0);
    }

    #[test]
    fn setup_and_decoding_failures_name_their_phase() {
        let failing_setup = script(
            &["Tally", "step"],
            &[Json::Array(vec![]), Json::parse("[100]").unwrap()],
        );
        let (outcome, _) = run(&case(failing_setup, vec![steps(1), steps(1)], None));
        assert_eq!(field(&outcome, "phase").unwrap().text(), "\"setup\"");
        assert_eq!(field(&outcome, "op_index").unwrap().as_i64(), Some(1));
        assert!(field(&outcome, "worker").is_none());

        let bad = script(&["step"], &[Json::parse(r#"["x"]"#).unwrap()]);
        let (outcome, _) = run(&case(tally(), vec![steps(1), bad], None));
        assert_eq!(error(&outcome).0, "InvalidInput");
        assert_eq!(field(&outcome, "worker").unwrap().as_i64(), Some(1));
    }

    #[test]
    fn a_stalled_run_leaves_its_workers_running() {
        let mut case = case(
            tally(),
            vec![repeated("wait", 1), repeated("wait", 1)],
            None,
        );
        case.deadline_ms = 100;
        let (outcome, workers) = run(&case);
        assert!(matches!(outcome.status, Status::Stalled), "{outcome:?}");
        assert_eq!(
            field(&outcome, "progress").unwrap().text(),
            r#"[{"worker":0,"completed":0,"in_op":true},{"worker":1,"completed":0,"in_op":true}]"#
        );
        assert_eq!(workers.still_running(), 2);
    }
}
