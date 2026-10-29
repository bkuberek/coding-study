//! The request file (docs/specs/runners.md#request-file and #bench-mode). The bridge already
//! knows the symbols and their types, so the runner reads only what routes a call: the job kind,
//! the compiled target ids, the inputs and the bench settings. `names` and `signature` are
//! ignored.

use crate::json::Json;

pub const PROTOCOL_VERSION: i64 = 1;

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
        Some("design" | "progressive") => Kind::Class,
        Some("concurrent") => {
            return Err(context(
                "the rust runner does not run concurrent jobs yet".into(),
            ))
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
    let cases = array(job, "cases")
        .and_then(|cases| cases.iter().map(parse_case).collect())
        .map_err(context)?;
    Ok(Job {
        job_id,
        kind,
        target,
        cases,
        bench: None,
    })
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
    let ops = array(value, "ops").map_err(|_| "a case needs input or ops".to_string())?;
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
    Ok(CallInput::Ops { ops, args })
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

    #[test]
    fn rejects_unknown_protocols_modes_and_concurrent_jobs() {
        assert!(parse_request(r#"{"protocol": 2, "mode": "test", "jobs": []}"#).is_err());
        assert!(parse_request(r#"{"protocol": 1, "mode": "debug", "jobs": []}"#).is_err());
        let concurrent = r#"{"protocol": 1, "mode": "test", "jobs": [{"job_id": "q",
            "kind": "concurrent", "target": {"compiled": "user"}, "cases": []}]}"#;
        let error = parse_request(concurrent).err().unwrap_or_default();
        assert!(error.contains("concurrent jobs"), "{error}");
    }
}
