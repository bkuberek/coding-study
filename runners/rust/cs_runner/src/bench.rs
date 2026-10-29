//! Bench mode (docs/specs/runners.md#bench-mode). Per size, in request order: each target makes
//! one check call, run like a test case, whose output is reported for output targets; warmup
//! samples follow until the timings settle; then the timed repetitions take turns across
//! targets; then each target's memory is measured once. Every call, or batch of calls, is
//! announced with `bench_start` first, so the CLI can attribute a hang.
//!
//! A sample makes `calls` back-to-back calls, each on its own freshly decoded input. Decoding
//! happens before the timed region, and results are dropped after it.

use std::any::Any;
use std::panic::{self, AssertUnwindSafe};
use std::time::Instant;

use crate::alloc;
use crate::clock::thread_cpu_ns;
use crate::events::{BenchPoint, Events, Outcome, Sample, Status, UserError};
use crate::harness::{bind, elapsed_ns, run_case, take_panic};
use crate::json::Json;
use crate::request::{BenchInput, BenchSettings, BenchTarget, CallInput, Job};
use crate::{Args, Class, Encode, Entry, InputError, Target};

/// The peak of the bytes one call held at once (docs/specs/performance-analysis.md#measurement).
const MEMORY_METRIC: &str = "heap_peak";
/// Warmup is settled when the coefficient of variation of the latest runs is low enough.
const CV_WINDOW: usize = 5;
const NANOS_PER_MILLI: u64 = 1_000_000;

/// What one prepared call returns. It is only held, until the sample ends, so freeing it is not
/// timed.
#[allow(dead_code)]
enum Kept {
    Value(Box<dyn Encode>),
    Sequence(Box<dyn Any>, Vec<Box<dyn Encode>>),
}

type Prepared = Box<dyn FnOnce() -> Kept>;

struct Code<'a> {
    spec: &'a BenchTarget,
    target: &'a Target,
    calls: usize,
}

struct BenchRun<'a> {
    job_id: &'a str,
    settings: &'a BenchSettings,
    events: &'a mut Events,
}

pub fn run_bench_jobs(targets: &[Target], jobs: &[Job], events: &mut Events) {
    for job in jobs {
        events.job_start(&job.job_id);
        if let Some(bench) = &job.bench {
            let mut loaded = Vec::new();
            for spec in &bench.targets {
                match bind(targets, &spec.compiled, job.kind) {
                    Ok(target) => loaded.push(Code {
                        spec,
                        target,
                        calls: 1,
                    }),
                    Err(error) => events.target_load_error(&job.job_id, &spec.target_id, &error),
                }
            }
            let mut run = BenchRun {
                job_id: &job.job_id,
                settings: &bench.settings,
                events,
            };
            run.run(loaded, &bench.inputs);
        }
        events.job_end(&job.job_id);
    }
}

impl BenchRun<'_> {
    fn run(&mut self, mut active: Vec<Code>, inputs: &[BenchInput]) {
        for input in inputs {
            active.retain_mut(|code| self.warm_up(code, input));
            active = self.repetitions(active, input);
            if self.settings.memory {
                active.retain_mut(|code| self.memory(code, input));
            }
        }
    }

    /// The check call and the warmup samples; false once the target is dropped.
    fn warm_up(&mut self, code: &mut Code, input: &BenchInput) -> bool {
        let point = self.start(code, input);
        let checked = run_case(code.target, &input.input);
        let duration = checked.duration_ns;
        match checked.status {
            Status::Ok(output) => {
                if code.spec.output {
                    self.events.bench_output(&point, output);
                }
            }
            _ => {
                self.events.bench_error(&point, checked);
                return false;
            }
        }
        if self.over_budget(&point, duration) {
            return false;
        }
        code.calls = self.batch(input, 1, duration);
        let mut runs = vec![duration];
        let started = Instant::now();
        while !self.settled(&runs) && elapsed_ns(started) < self.budget_ns() {
            let Some(sample) = self.sample(code, input) else {
                return false;
            };
            if self.over_budget(&point, sample.per_call_ns()) {
                return false;
            }
            runs.push(sample.per_call_ns());
            code.calls = self.batch(input, code.calls, sample.wall_ns);
        }
        true
    }

    fn repetitions<'a>(&mut self, mut active: Vec<Code<'a>>, input: &BenchInput) -> Vec<Code<'a>> {
        for rep in 1..=self.settings.reps {
            active.retain_mut(|code| {
                let Some(sample) = self.sample(code, input) else {
                    return false;
                };
                let point = self.point(code, input);
                if self.over_budget(&point, sample.per_call_ns()) {
                    return false;
                }
                self.events.bench_sample(&point, rep, &sample);
                true
            });
        }
        active
    }

    /// The peak memory of one call; false when the call fails.
    fn memory(&mut self, code: &mut Code, input: &BenchInput) -> bool {
        let point = self.start(code, input);
        let Some(call) = self.prepared(code, input, &point) else {
            return false;
        };
        let (result, bytes) = alloc::measure(|| panic::catch_unwind(AssertUnwindSafe(call)));
        if result.is_err() {
            let error = take_panic(code.target.file);
            self.events.bench_error(&point, Outcome::raised(error, 0));
            return false;
        }
        drop(result);
        self.events.bench_memory(&point, MEMORY_METRIC, bytes);
        true
    }

    /// One timed sample; `None` (after `bench_error`) when the code fails.
    fn sample(&mut self, code: &Code, input: &BenchInput) -> Option<Sample> {
        let point = self.start(code, input);
        let mut prepared = Vec::with_capacity(code.calls);
        for _ in 0..code.calls {
            prepared.push(self.prepared(code, input, &point)?);
        }
        let mut kept = Vec::with_capacity(code.calls);
        let cpu_started = thread_cpu_ns();
        let started = Instant::now();
        let result = panic::catch_unwind(AssertUnwindSafe(|| {
            for call in prepared {
                kept.push(call());
            }
        }));
        let wall_ns = elapsed_ns(started);
        let cpu_ns = thread_cpu_ns().saturating_sub(cpu_started);
        drop(kept);
        if result.is_err() {
            let error = take_panic(code.target.file);
            self.events
                .bench_error(&point, Outcome::raised(error, wall_ns));
            return None;
        }
        Some(Sample {
            wall_ns,
            cpu_ns,
            calls: code.calls,
        })
    }

    fn prepared(
        &mut self,
        code: &Code,
        input: &BenchInput,
        point: &BenchPoint,
    ) -> Option<Prepared> {
        match prepare(&code.target.entry, &input.input) {
            Ok(call) => Some(call),
            Err(error) => {
                let outcome = Outcome::raised(UserError::invalid_input(error.0), 0);
                self.events.bench_error(point, outcome);
                None
            }
        }
    }

    fn settled(&self, runs: &[u64]) -> bool {
        if runs.len() >= self.settings.warmup_max {
            return true;
        }
        if runs.len() < self.settings.warmup_min {
            return false;
        }
        let latest = &runs[runs.len().saturating_sub(CV_WINDOW)..];
        latest.len() > 1 && coefficient_of_variation(latest) <= self.settings.warmup_cv
    }

    /// The calls per sample that make one sample last at least `min_sample_ns`.
    fn batch(&self, input: &BenchInput, calls: usize, sample_ns: u64) -> usize {
        batch_size(
            calls,
            sample_ns,
            self.settings.min_sample_ns,
            input.max_batch,
        )
    }

    fn over_budget(&mut self, point: &BenchPoint, per_call_ns: u64) -> bool {
        if per_call_ns <= self.budget_ns() {
            return false;
        }
        self.events.bench_budget_exceeded(point, per_call_ns);
        true
    }

    fn budget_ns(&self) -> u64 {
        self.settings.budget_ms.saturating_mul(NANOS_PER_MILLI)
    }

    fn start(&mut self, code: &Code, input: &BenchInput) -> BenchPoint {
        let point = self.point(code, input);
        self.events.bench_start(&point);
        point
    }

    fn point(&self, code: &Code, input: &BenchInput) -> BenchPoint {
        BenchPoint {
            job_id: self.job_id.to_string(),
            target_id: code.spec.target_id.clone(),
            size: input.size,
        }
    }
}

/// Decodes fresh arguments for one uncaptured call of a whole case.
fn prepare(entry: &Entry, input: &CallInput) -> Result<Prepared, InputError> {
    match (entry, input) {
        (Entry::Function(function), CallInput::Named(fields)) => {
            let call = function(&Args::Named(fields))?;
            Ok(Box::new(move || Kept::Value(call())))
        }
        (Entry::Class(class), CallInput::Ops { ops, args }) => prepare_operations(class, ops, args),
        _ => Err(InputError("the input does not fit the job's kind".into())),
    }
}

fn prepare_operations(
    class: &Class,
    ops: &[String],
    args: &[Vec<Json>],
) -> Result<Prepared, InputError> {
    if ops.first().map(String::as_str) != Some(class.name) || ops.len() != args.len() {
        return Err(InputError(format!(
            "a class job takes an operation sequence that starts with \"{}\"",
            class.name
        )));
    }
    let make = (class.construct)(&Args::Positional(&args[0]))?;
    let methods = ops[1..]
        .iter()
        .zip(&args[1..])
        .map(|(op, arguments)| (class.method)(op, &Args::Positional(arguments)))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(Box::new(move || {
        let mut instance = make();
        let outputs = methods
            .into_iter()
            .map(|method| method(&mut *instance))
            .collect();
        Kept::Sequence(instance, outputs)
    }))
}

fn batch_size(calls: usize, sample_ns: u64, min_sample_ns: u64, max_batch: usize) -> usize {
    if sample_ns >= min_sample_ns {
        return calls;
    }
    let wanted = (calls as f64 * min_sample_ns as f64 / sample_ns.max(1) as f64).ceil() as usize;
    calls.max(wanted.min(max_batch))
}

fn coefficient_of_variation(values: &[u64]) -> f64 {
    let count = values.len() as f64;
    let mean = values.iter().map(|value| *value as f64).sum::<f64>() / count;
    if mean == 0.0 {
        return 0.0;
    }
    let squares: f64 = values
        .iter()
        .map(|value| (*value as f64 - mean).powi(2))
        .sum();
    (squares / count).sqrt() / mean
}

#[cfg(test)]
mod tests {
    use super::{batch_size, coefficient_of_variation};

    #[test]
    fn short_samples_grow_their_batch_up_to_the_cap() {
        assert_eq!(batch_size(1, 1_000, 20_000_000, 100_000), 20_000);
        assert_eq!(batch_size(1, 1_000, 20_000_000, 500), 500);
        assert_eq!(batch_size(7, 30_000_000, 20_000_000, 500), 7);
    }

    #[test]
    fn coefficient_of_variation_is_the_relative_spread() {
        assert_eq!(coefficient_of_variation(&[5, 5, 5]), 0.0);
        assert!((coefficient_of_variation(&[90, 110]) - 0.1).abs() < 1e-9);
    }
}
