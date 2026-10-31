//! The JSON Lines event stream (docs/specs/runners.md#event-stream). Each event is one
//! unbuffered write, so the CLI sees it as soon as it is written.

use std::fs::File;
use std::io::Write;

use crate::json::Json;
use crate::request::PROTOCOL_VERSION;

const RUNNER_NAME: &str = "rust";
/// Tells the CLI that this runner runs concurrent jobs (docs/specs/runners.md#capability).
const STRESS_FEATURE: &str = "stress";
/// Grading jobs of project problems, whose crate the harness links (runners.md#rust-projects).
const PROJECT_FEATURE: &str = "project";

/// The `error` object of an event.
#[derive(Clone, Debug, PartialEq)]
pub struct UserError {
    pub error_type: String,
    pub message: String,
    /// Frames in the target's file, innermost last; omitted when empty.
    pub trace: String,
}

impl UserError {
    pub fn new(error_type: &str, message: impl Into<String>) -> Self {
        UserError {
            error_type: error_type.to_string(),
            message: message.into(),
            trace: String::new(),
        }
    }

    /// An input that does not fit the declared parameters.
    pub fn invalid_input(message: impl Into<String>) -> Self {
        UserError::new("InvalidInput", message)
    }

    fn to_json(&self) -> Json {
        let mut fields = vec![
            ("type".to_string(), Json::String(self.error_type.clone())),
            ("message".to_string(), Json::String(self.message.clone())),
        ];
        if !self.trace.is_empty() {
            fields.push(("trace".to_string(), Json::String(self.trace.clone())));
        }
        Json::Object(fields)
    }
}

#[derive(Debug)]
pub enum Status {
    Ok(Json),
    Error {
        error: UserError,
        /// Class kinds: the failing operation and the outputs before it.
        op: Option<(usize, Vec<Json>)>,
    },
    InvalidOutput(String),
    /// A stress run whose workers were unfinished at its deadline.
    Stalled,
}

/// What one call sequence produced: a case, or a bench check call.
#[derive(Debug)]
pub struct Outcome {
    pub status: Status,
    pub duration_ns: u64,
    pub stdout: String,
    /// What a stress run adds after the status fields: the probe sections of a completed run, or
    /// where a failed run failed and which workers had not finished.
    pub stress: Vec<(&'static str, Json)>,
}

impl Outcome {
    pub fn returned(output: Json, duration_ns: u64) -> Self {
        Outcome::with(Status::Ok(output), duration_ns)
    }

    pub fn raised(error: UserError, duration_ns: u64) -> Self {
        Outcome::with(Status::Error { error, op: None }, duration_ns)
    }

    pub fn invalid(reason: String, duration_ns: u64) -> Self {
        Outcome::with(Status::InvalidOutput(reason), duration_ns)
    }

    pub fn stalled(duration_ns: u64) -> Self {
        Outcome::with(Status::Stalled, duration_ns)
    }

    fn with(status: Status, duration_ns: u64) -> Self {
        Outcome {
            status,
            duration_ns,
            stdout: String::new(),
            stress: Vec::new(),
        }
    }

    /// The outcome's part of a `case_result` or `bench_error`; empty stdout is omitted.
    fn fields(self) -> Vec<(&'static str, Json)> {
        let mut fields = Vec::new();
        match self.status {
            Status::Ok(output) => {
                fields.push(("status", text("ok")));
                fields.push(("output", output));
            }
            Status::Error { error, op } => {
                fields.push(("status", text("error")));
                fields.push(("error", error.to_json()));
                if let Some((index, partial)) = op {
                    fields.push(("op_index", Json::Int(index as i64)));
                    fields.push(("partial_output", Json::Array(partial)));
                }
            }
            Status::InvalidOutput(reason) => {
                fields.push(("status", text("invalid_output")));
                fields.push(("reason", Json::String(reason)));
            }
            Status::Stalled => fields.push(("status", text("stalled"))),
        }
        fields.extend(self.stress);
        fields.push(("duration_ns", nanoseconds(self.duration_ns)));
        if !self.stdout.is_empty() {
            fields.push(("stdout", Json::String(self.stdout)));
        }
        fields
    }
}

fn text(value: &str) -> Json {
    Json::String(value.to_string())
}

pub fn nanoseconds(value: u64) -> Json {
    Json::Int(i64::try_from(value).unwrap_or(i64::MAX))
}

/// One target at one input size of a bench job; every bench event names one.
#[derive(Clone)]
pub struct BenchPoint {
    pub job_id: String,
    pub target_id: String,
    pub size: i64,
}

impl BenchPoint {
    fn fields(&self, event: &str) -> Vec<(&'static str, Json)> {
        vec![
            ("event", text(event)),
            ("job_id", text(&self.job_id)),
            ("target_id", text(&self.target_id)),
            ("size", Json::Int(self.size)),
        ]
    }
}

/// `calls` back-to-back calls, each on a fresh input.
pub struct Sample {
    pub wall_ns: u64,
    pub cpu_ns: u64,
    pub calls: usize,
}

impl Sample {
    pub fn per_call_ns(&self) -> u64 {
        self.wall_ns / self.calls.max(1) as u64
    }
}

pub struct Events {
    file: File,
}

impl Events {
    pub fn new(file: File) -> Self {
        Events { file }
    }

    fn emit(&mut self, fields: Vec<(&'static str, Json)>) {
        let object = Json::Object(
            fields
                .into_iter()
                .map(|(key, value)| (key.to_string(), value))
                .collect(),
        );
        let mut line = object.text();
        line.push('\n');
        let _ = self.file.write_all(line.as_bytes());
    }

    pub fn hello(&mut self) {
        self.emit(vec![
            ("event", text("hello")),
            ("runner", text(RUNNER_NAME)),
            ("protocol", Json::Int(PROTOCOL_VERSION)),
            ("runtime", text(env!("CS_RUSTC_VERSION"))),
            (
                "features",
                Json::Array(vec![text(STRESS_FEATURE), text(PROJECT_FEATURE)]),
            ),
        ]);
    }

    /// Follows a stress run's `case_result` when its worker threads still run; the runner then
    /// exits for a restart, without `bye`.
    pub fn restart_requested(&mut self, reason: &str) {
        self.emit(vec![
            ("event", text("restart_requested")),
            ("reason", text(reason)),
        ]);
    }

    pub fn job_start(&mut self, job_id: &str) {
        self.emit(vec![("event", text("job_start")), ("job_id", text(job_id))]);
    }

    pub fn job_end(&mut self, job_id: &str) {
        self.emit(vec![("event", text("job_end")), ("job_id", text(job_id))]);
    }

    pub fn case_start(&mut self, job_id: &str, case_id: &str) {
        self.emit(vec![
            ("event", text("case_start")),
            ("job_id", text(job_id)),
            ("case_id", text(case_id)),
        ]);
    }

    pub fn case_result(&mut self, job_id: &str, case_id: &str, outcome: Outcome) {
        let mut fields = vec![
            ("event", text("case_result")),
            ("job_id", text(job_id)),
            ("case_id", text(case_id)),
        ];
        fields.extend(outcome.fields());
        self.emit(fields);
    }

    pub fn load_error(&mut self, job_id: &str, error: &UserError) {
        self.emit(vec![
            ("event", text("load_error")),
            ("job_id", text(job_id)),
            ("error", error.to_json()),
        ]);
    }

    /// Bench mode's `load_error`: one target did not load, the others still run.
    pub fn target_load_error(&mut self, job_id: &str, target_id: &str, error: &UserError) {
        self.emit(vec![
            ("event", text("load_error")),
            ("job_id", text(job_id)),
            ("target_id", text(target_id)),
            ("error", error.to_json()),
        ]);
    }

    pub fn bench_start(&mut self, point: &BenchPoint) {
        self.emit(point.fields("bench_start"));
    }

    pub fn bench_output(&mut self, point: &BenchPoint, output: Json) {
        let mut fields = point.fields("bench_output");
        fields.push(("output", output));
        self.emit(fields);
    }

    pub fn bench_error(&mut self, point: &BenchPoint, outcome: Outcome) {
        let mut fields = point.fields("bench_error");
        fields.extend(outcome.fields());
        self.emit(fields);
    }

    pub fn bench_sample(&mut self, point: &BenchPoint, rep: usize, sample: &Sample) {
        let mut fields = point.fields("bench_sample");
        fields.extend([
            ("rep", Json::Int(rep as i64)),
            ("wall_ns", nanoseconds(sample.wall_ns)),
            ("cpu_ns", nanoseconds(sample.cpu_ns)),
            ("calls", Json::Int(sample.calls as i64)),
        ]);
        self.emit(fields);
    }

    pub fn bench_memory(&mut self, point: &BenchPoint, metric: &str, bytes: u64) {
        let mut fields = point.fields("bench_memory");
        fields.extend([("metric", text(metric)), ("bytes", nanoseconds(bytes))]);
        self.emit(fields);
    }

    pub fn bench_budget_exceeded(&mut self, point: &BenchPoint, wall_ns: u64) {
        let mut fields = point.fields("bench_budget_exceeded");
        fields.push(("wall_ns", nanoseconds(wall_ns)));
        self.emit(fields);
    }

    pub fn bye(&mut self) {
        self.emit(vec![("event", text("bye"))]);
    }
}

#[cfg(test)]
mod tests {
    use super::{Outcome, Status, UserError};
    use crate::json::Json;

    fn line(outcome: Outcome) -> String {
        Json::Object(
            outcome
                .fields()
                .into_iter()
                .map(|(key, value)| (key.to_string(), value))
                .collect(),
        )
        .text()
    }

    #[test]
    fn an_ok_result_has_output_duration_and_captured_text() {
        let mut outcome = Outcome::returned(Json::Int(3), 41);
        outcome.stdout = "hi\n".into();
        assert_eq!(
            line(outcome),
            r#"{"status":"ok","output":3,"duration_ns":41,"stdout":"hi\n"}"#
        );
    }

    #[test]
    fn an_operation_error_has_its_index_and_the_outputs_before_it() {
        let error = UserError::new("panic", "boom");
        let outcome = Outcome {
            status: Status::Error {
                error,
                op: Some((2, vec![Json::Null, Json::Int(1)])),
            },
            duration_ns: 5,
            stdout: String::new(),
            stress: Vec::new(),
        };
        assert_eq!(
            line(outcome),
            r#"{"status":"error","error":{"type":"panic","message":"boom"},"op_index":2,"partial_output":[null,1],"duration_ns":5}"#
        );
    }
}
