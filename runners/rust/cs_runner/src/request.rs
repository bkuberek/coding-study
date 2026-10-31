//! The request file (docs/specs/runners.md#request-file and #bench-mode). The bridge already
//! knows the symbols and their types, so the runner reads only what routes a call: the job kind,
//! the compiled target ids, the inputs and the bench settings. `names` and `signature` are
//! ignored.

use crate::json::Json;

pub const PROTOCOL_VERSION: i64 = 1;
/// The only concurrency model Rust runs (docs/specs/problem-format.md#models-and-language-support).
const THREADS_MODEL: &str = "threads";

#[derive(Debug, PartialEq)]
pub enum Mode {
    Test,
    Bench,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Kind {
    Function,
    /// `design` and `progressive`: an operation sequence on one instance.
    Class,
    /// Sequential cases like a class's, then stress runs whose workers share one instance.
    Concurrent,
}

pub struct Request {
    pub mode: Mode,
    pub jobs: Vec<Job>,
}

pub struct Job {
    pub job_id: String,
    pub kind: Kind,
    /// Test mode: `target.compiled`, the id of code linked into this binary.
    pub target: String,
    pub cases: Vec<Case>,
    pub bench: Option<BenchJob>,
}

pub struct Case {
    pub id: String,
    pub input: CallInput,
}

/// What one case or bench input passes.
pub enum CallInput {
    /// Function kind: arguments by canonical parameter name.
    Named(Vec<(String, Json)>),
    /// Class kinds: operation names and their argument lists, which may differ in length (a
    /// case error, reported on operation 0).
    Ops {
        ops: Vec<String>,
        args: Vec<Vec<Json>>,
    },
    /// A stress run of a concurrent job, which the CLI expanded into literal worker scripts
    /// (docs/specs/runners.md#concurrent-jobs).
    Stress(Box<StressCase>),
}

pub struct StressCase {
    pub seed: i64,
    pub deadline_ms: u64,
    pub yield_probability: f64,
    pub max_yields: u64,
    /// Starts with the constructor.
    pub setup: Script,
    pub workers: Vec<Script>,
    pub final_script: Option<Script>,
}

/// Operation names and their argument lists, which may differ in length (a run error).
#[derive(Clone)]
pub struct Script {
    pub ops: Vec<String>,
    pub args: Vec<Vec<Json>>,
}

pub struct BenchJob {
    pub targets: Vec<BenchTarget>,
    pub inputs: Vec<BenchInput>,
    pub settings: BenchSettings,
}

pub struct BenchTarget {
    pub target_id: String,
    pub compiled: String,
    pub output: bool,
}

pub struct BenchInput {
    pub size: i64,
    pub input: CallInput,
    pub max_batch: usize,
}

pub struct BenchSettings {
    pub reps: usize,
    pub warmup_min: usize,
    pub warmup_max: usize,
    pub warmup_cv: f64,
    pub budget_ms: u64,
    pub memory: bool,
    pub min_sample_ns: u64,
}

/// Any error makes the request bad (exit 2), reported before a case starts.
pub fn parse_request(text: &str) -> Result<Request, String> {
    let root = Json::parse(text)?;
    let protocol = root.get("protocol").and_then(Json::as_i64);
    if protocol != Some(PROTOCOL_VERSION) {
        return Err(format!(
            "unknown protocol {}",
            describe(root.get("protocol"))
        ));
    }
    let mode = match root.get("mode").and_then(Json::as_str) {
        Some("test") => Mode::Test,
        Some("bench") => Mode::Bench,
        _ => return Err(format!("unknown mode {}", describe(root.get("mode")))),
    };
    let jobs = root
        .get("jobs")
        .and_then(Json::as_array)
        .ok_or("missing jobs")?;
    let jobs = jobs
        .iter()
        .map(|job| parse_job(job, &mode))
        .collect::<Result<_, _>>()?;
    Ok(Request { mode, jobs })
}

fn describe(value: Option<&Json>) -> String {
    value.map_or_else(|| "(missing)".to_string(), Json::text)
}

fn text(value: &Json, key: &str) -> Result<String, String> {
    value
        .get(key)
        .and_then(Json::as_str)
        .map(str::to_string)
        .ok_or_else(|| format!("missing {key}"))
}

fn array<'a>(value: &'a Json, key: &str) -> Result<&'a [Json], String> {
    value
        .get(key)
        .and_then(Json::as_array)
        .ok_or_else(|| format!("missing {key}"))
}

fn count(value: &Json, key: &str) -> Result<usize, String> {
    value
        .get(key)
        .and_then(Json::as_i64)
        .and_then(|number| usize::try_from(number).ok())
        .ok_or_else(|| format!("missing {key}"))
}

fn parse_job(job: &Json, mode: &Mode) -> Result<Job, String> {
    let job_id = text(job, "job_id")?;
    let context = |error: String| format!("job \"{job_id}\": {error}");
    let kind = match job.get("kind").and_then(Json::as_str) {
        Some("function") => Kind::Function,
        Some("design" | "progressive" | "project") => Kind::Class,
        Some("concurrent") => {
            check_concurrent(job, mode).map_err(context)?;
            Kind::Concurrent
        }
        _ => {
            return Err(context(format!(
                "unknown kind {}",
                describe(job.get("kind"))
            )))
        }
    };
    if *mode == Mode::Bench {
        let bench = parse_bench(job).map_err(context)?;
        return Ok(Job {
            job_id,
            kind,
            target: String::new(),
            cases: Vec::new(),
            bench: Some(bench),
        });
    }
    let target = compiled(job).map_err(context)?;
    let cases: Vec<Case> = array(job, "cases")
        .and_then(|cases| cases.iter().map(parse_case).collect())
        .map_err(context)?;
    let stress = cases
        .iter()
        .any(|case| matches!(case.input, CallInput::Stress(_)));
    if stress && kind != Kind::Concurrent {
        return Err(context("only a concurrent job has stress cases".into()));
    }
    Ok(Job {
        job_id,
        kind,
        target,
        cases,
        bench: None,
    })
}

fn check_concurrent(job: &Json, mode: &Mode) -> Result<(), String> {
    let model = job.get("model").and_then(Json::as_str);
    if model != Some(THREADS_MODEL) {
        return Err(format!(
            "the rust runner runs the threads model only, not {}",
            describe(job.get("model"))
        ));
    }
    if *mode == Mode::Bench {
        return Err("concurrent problems have no bench".into());
    }
    Ok(())
}

/// `target.compiled` of a job or a bench target.
fn compiled(value: &Json) -> Result<String, String> {
    text(value.get("target").ok_or("missing target")?, "compiled")
}

fn parse_case(case: &Json) -> Result<Case, String> {
    Ok(Case {
        id: text(case, "id")?,
        input: parse_input(case)?,
    })
}

fn parse_input(value: &Json) -> Result<CallInput, String> {
    if let Some(Json::Object(fields)) = value.get("input") {
        return Ok(CallInput::Named(fields.clone()));
    }
    if let Some(stress) = value.get("stress") {
        return parse_stress(stress).map(|stress| CallInput::Stress(Box::new(stress)));
    }
    array(value, "ops").map_err(|_| "a case needs input, ops or stress".to_string())?;
    let Script { ops, args } = parse_script(value)?;
    Ok(CallInput::Ops { ops, args })
}

fn parse_stress(stress: &Json) -> Result<StressCase, String> {
    let perturb = stress.get("perturb").ok_or("missing perturb")?;
    let setup = parse_script(stress.get("setup").ok_or("missing setup")?)?;
    if setup.ops.is_empty() {
        return Err("a stress case's setup needs the constructor".into());
    }
    Ok(StressCase {
        seed: stress
            .get("seed")
            .and_then(Json::as_i64)
            .ok_or("missing seed")?,
        deadline_ms: count(stress, "deadline_ms")? as u64,
        yield_probability: perturb
            .get("yield_probability")
            .and_then(Json::as_f64)
            .ok_or("missing yield_probability")?,
        max_yields: count(perturb, "max_yields")? as u64,
        setup,
        workers: array(stress, "workers")?
            .iter()
            .map(parse_script)
            .collect::<Result<_, _>>()?,
        final_script: stress.get("final").map(parse_script).transpose()?,
    })
}

fn parse_script(value: &Json) -> Result<Script, String> {
    let ops = array(value, "ops")?;
    let args = array(value, "args")?;
    let ops = ops
        .iter()
        .map(|op| {
            op.as_str()
                .map(str::to_string)
                .ok_or("an op must be a string")
        })
        .collect::<Result<_, _>>()?;
    let args = args
        .iter()
        .map(|list| {
            list.as_array()
                .map(<[Json]>::to_vec)
                .ok_or("args must be arrays")
        })
        .collect::<Result<_, _>>()?;
    Ok(Script { ops, args })
}

fn parse_bench(job: &Json) -> Result<BenchJob, String> {
    let targets = array(job, "targets")?
        .iter()
        .map(|target| {
            Ok(BenchTarget {
                target_id: text(target, "target_id")?,
                compiled: compiled(target)?,
                output: target.get("output").and_then(Json::as_bool) == Some(true),
            })
        })
        .collect::<Result<Vec<_>, String>>()?;
    if targets.is_empty() {
        return Err("a bench job needs targets".into());
    }
    let inputs = array(job, "inputs")?
        .iter()
        .map(|input| {
            Ok(BenchInput {
                size: input
                    .get("size")
                    .and_then(Json::as_i64)
                    .ok_or("missing size")?,
                input: parse_input(input)?,
                max_batch: count(input, "max_batch")?.max(1),
            })
        })
        .collect::<Result<_, String>>()?;
    let settings = job.get("settings").ok_or("missing settings")?;
    let warmup = settings.get("warmup").ok_or("missing warmup")?;
    Ok(BenchJob {
        targets,
        inputs,
        settings: BenchSettings {
            reps: count(settings, "reps")?,
            warmup_min: count(warmup, "min")?,
            warmup_max: count(warmup, "max")?,
            warmup_cv: warmup
                .get("cv")
                .and_then(Json::as_f64)
                .ok_or("missing cv")?,
            budget_ms: count(settings, "budget_ms")? as u64,
            memory: settings.get("memory").and_then(Json::as_bool) == Some(true),
            min_sample_ns: count(settings, "min_sample_ns")? as u64,
        },
    })
}

#[cfg(test)]
mod tests {
    use super::{parse_request, CallInput, Kind, Mode};

    #[test]
    fn reads_a_function_job() {
        let request = parse_request(
            r#"{"protocol": 1, "mode": "test", "jobs": [{"job_id": "two-sum", "kind": "function",
            "target": {"compiled": "user"}, "names": {}, "signature": {},
            "cases": [{"id": "ex1", "input": {"nums": [2, 7], "target": 9}}]}]}"#,
        )
        .unwrap();
        let job = &request.jobs[0];
        assert_eq!(
            (&job.job_id[..], job.kind, &job.target[..]),
            ("two-sum", Kind::Function, "user")
        );
        let CallInput::Named(fields) = &job.cases[0].input else {
            panic!("expected named inputs");
        };
        assert_eq!(fields.len(), 2);
    }

    #[test]
    fn reads_an_operation_sequence() {
        let request = parse_request(
            r#"{"protocol": 1, "mode": "test", "jobs": [{"job_id": "lru", "kind": "design",
            "target": {"compiled": "ref/hash-map"},
            "cases": [{"id": "ex1", "ops": ["LRUCache", "get"], "args": [[2], [1]]}]}]}"#,
        )
        .unwrap();
        let CallInput::Ops { ops, args } = &request.jobs[0].cases[0].input else {
            panic!("expected operations");
        };
        assert_eq!((ops.len(), args.len()), (2, 2));
        assert_eq!(request.jobs[0].kind, Kind::Class);
    }

    #[test]
    fn a_project_job_is_a_class_job() {
        let request = parse_request(
            r#"{"protocol": 1, "mode": "test", "jobs": [{"job_id": "bank", "kind": "project",
            "target": {"compiled": "user"},
            "cases": [{"id": "ex1", "ops": ["Bank", "deposit"], "args": [[], [1, "a", 5]]}]}]}"#,
        )
        .unwrap();
        assert_eq!(request.jobs[0].kind, Kind::Class);
    }

    #[test]
    fn reads_a_bench_job() {
        let request = parse_request(
            r#"{"protocol": 1, "mode": "bench", "jobs": [{"job_id": "two-sum", "kind": "function",
            "targets": [{"target_id": "user", "target": {"compiled": "user"}, "output": true}],
            "inputs": [{"size": 10, "input": {"nums": [1]}, "max_batch": 100}],
            "settings": {"reps": 7, "warmup": {"min": 1, "max": 3, "cv": 0.05}, "budget_ms": 2000,
            "memory": true, "min_sample_ns": 20000000}}]}"#,
        )
        .unwrap();
        assert_eq!(request.mode, Mode::Bench);
        let bench = request.jobs[0].bench.as_ref().unwrap();
        assert!(bench.targets[0].output);
        assert_eq!(
            (bench.inputs[0].max_batch, bench.settings.warmup_max),
            (100, 3)
        );
    }

    const STRESS_CASE: &str = r#"{"id": "s1:thread:0", "stress": {"seed": 1000,
        "deadline_ms": 5000, "perturb": {"yield_probability": 0.05, "max_yields": 3,
        "python_granularity": "line"}, "setup": {"ops": ["Queue"], "args": [[4]]},
        "workers": [{"ops": ["put", "@pause"], "args": [[1], [2]]}, {"ops": ["take"], "args": [[]]}],
        "final": {"ops": ["size"], "args": [[]]}}}"#;

    fn concurrent(model: &str, mode: &str, case: &str) -> String {
        format!(
            r#"{{"protocol": 1, "mode": "{mode}", "jobs": [{{"job_id": "q", "kind": "concurrent",
            "model": "{model}", "target": {{"compiled": "user"}}, "cases": [{case}],
            "targets": [{{"target_id": "user", "target": {{"compiled": "user"}}}}], "inputs": [],
            "settings": {{}}}}]}}"#
        )
    }

    #[test]
    fn reads_a_concurrent_job_with_stress_cases() {
        let request = parse_request(&concurrent("threads", "test", STRESS_CASE));
        assert!(request.is_ok(), "{:?}", request.err());
        let job = &request.unwrap().jobs[0];
        assert_eq!(job.kind, Kind::Concurrent);
        let CallInput::Stress(stress) = &job.cases[0].input else {
            panic!("expected a stress case");
        };
        assert_eq!(
            (stress.seed, stress.deadline_ms, stress.max_yields),
            (1000, 5000, 3)
        );
        assert_eq!(stress.setup.ops, ["Queue"]);
        assert_eq!(stress.workers[0].ops, ["put", "@pause"]);
        assert_eq!(
            stress.final_script.as_ref().map(|script| script.ops.len()),
            Some(1)
        );
    }

    #[test]
    fn rejects_the_async_model_a_concurrent_bench_and_stray_stress_cases() {
        let errors = [
            parse_request(&concurrent("async", "test", STRESS_CASE)),
            parse_request(&concurrent("threads", "bench", STRESS_CASE)),
            parse_request(
                &concurrent("threads", "test", STRESS_CASE).replace("concurrent", "design"),
            ),
        ]
        .map(|request| request.err().unwrap_or_default());
        assert!(errors[0].contains("threads model only"), "{}", errors[0]);
        assert!(errors[1].contains("no bench"), "{}", errors[1]);
        assert!(errors[2].contains("only a concurrent job"), "{}", errors[2]);
    }

    #[test]
    fn rejects_unknown_protocols_and_modes() {
        assert!(parse_request(r#"{"protocol": 2, "mode": "test", "jobs": []}"#).is_err());
        assert!(parse_request(r#"{"protocol": 1, "mode": "debug", "jobs": []}"#).is_err());
    }
}
