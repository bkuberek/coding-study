use std::collections::HashMap;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Status {
    Queued,
    Running,
    Done,
    Failed,
    Cancelled,
}

impl Status {
    fn name(self) -> &'static str {
        match self {
            Status::Queued => "QUEUED",
            Status::Running => "RUNNING",
            Status::Done => "DONE",
            Status::Failed => "FAILED",
            Status::Cancelled => "CANCELLED",
        }
    }
}

/// A job's position in `JobScheduler::jobs` is its submission sequence number, and every link
/// between jobs is such a position.
struct Job {
    id: String,
    tenant: String,
    priority: i32,
    depends_on: Vec<usize>,
    status: Status,
    not_before: i64,
    failures: i32,
    dependents: Vec<usize>,
}

#[derive(Clone, Copy)]
struct RateLimit {
    limit: i32,
    window: i64,
}

#[derive(Clone, Copy, Default)]
struct RetryPolicy {
    max_retries: i32,
    base_delay: i64,
}

impl RetryPolicy {
    /// The wait before the next start, or `None` when no retry is left.
    fn delay_after(&self, failures: i32) -> Option<i64> {
        if failures > self.max_retries {
            return None;
        }
        Some(self.base_delay * 2_i64.pow((failures - 1) as u32))
    }
}

pub struct JobScheduler {
    jobs: Vec<Job>,
    positions: HashMap<String, usize>,
    /// Every `Queued` job, sorted by `order`.
    queue: Vec<usize>,
    /// Tenant to its start times, ascending.
    starts: HashMap<String, Vec<i64>>,
    limits: HashMap<String, RateLimit>,
    policies: HashMap<String, RetryPolicy>,
}

impl JobScheduler {
    pub fn new() -> Self {
        JobScheduler {
            jobs: Vec::new(),
            positions: HashMap::new(),
            queue: Vec::new(),
            starts: HashMap::new(),
            limits: HashMap::new(),
            policies: HashMap::new(),
        }
    }

    // Level 1
    pub fn submit(
        &mut self,
        timestamp: i64,
        job_id: String,
        tenant: String,
        priority: i32,
    ) -> bool {
        self.submit_after(timestamp, job_id, tenant, priority, Vec::new())
    }

    // Level 1
    pub fn run_next(&mut self, timestamp: i64) -> String {
        let startable = self
            .queue
            .iter()
            .copied()
            .find(|&position| self.can_start(position, timestamp));
        let Some(position) = startable else {
            return String::new();
        };
        self.unqueue(position);
        let job = &mut self.jobs[position];
        job.status = Status::Running;
        self.starts
            .entry(job.tenant.clone())
            .or_default()
            .push(timestamp);
        job.id.clone()
    }

    // Level 1
    pub fn status(&mut self, timestamp: i64, job_id: String) -> String {
        match self.positions.get(&job_id) {
            Some(&position) => self.jobs[position].status.name().to_string(),
            None => String::new(),
        }
    }

    // Level 1
    pub fn queued(&mut self, timestamp: i64) -> i32 {
        self.queue.len() as i32
    }

    // Level 2
    pub fn set_rate_limit(&mut self, timestamp: i64, tenant: String, limit: i32, window_ms: i64) {
        self.limits.insert(
            tenant,
            RateLimit {
                limit,
                window: window_ms,
            },
        );
    }

    // Level 3
    pub fn set_retry_policy(
        &mut self,
        timestamp: i64,
        tenant: String,
        max_retries: i32,
        base_delay_ms: i64,
    ) {
        self.policies.insert(
            tenant,
            RetryPolicy {
                max_retries,
                base_delay: base_delay_ms,
            },
        );
    }

    // Level 3
    pub fn complete(&mut self, timestamp: i64, job_id: String) -> bool {
        match self.positions.get(&job_id) {
            Some(&position) if self.jobs[position].status == Status::Running => {
                self.jobs[position].status = Status::Done;
                true
            }
            _ => false,
        }
    }

    // Level 3
    pub fn fail(&mut self, timestamp: i64, job_id: String) -> i64 {
        let position = match self.positions.get(&job_id) {
            Some(&position) if self.jobs[position].status == Status::Running => position,
            _ => return -1,
        };
        let job = &mut self.jobs[position];
        job.failures += 1;
        let policy = self.policies.get(&job.tenant).copied().unwrap_or_default();
        match policy.delay_after(job.failures) {
            None => {
                job.status = Status::Failed;
                self.cancel_dependents(position);
                0
            }
            Some(delay) => {
                job.not_before = timestamp + delay;
                let not_before = job.not_before;
                self.enqueue(position);
                not_before
            }
        }
    }

    // Level 4
    pub fn submit_after(
        &mut self,
        timestamp: i64,
        job_id: String,
        tenant: String,
        priority: i32,
        depends_on: Vec<String>,
    ) -> bool {
        if self.positions.contains_key(&job_id) {
            return false;
        }
        let mut dependencies = Vec::with_capacity(depends_on.len());
        for dependency in &depends_on {
            match self.positions.get(dependency) {
                Some(&position)
                    if !matches!(
                        self.jobs[position].status,
                        Status::Failed | Status::Cancelled
                    ) =>
                {
                    dependencies.push(position)
                }
                _ => return false,
            }
        }
        let position = self.jobs.len();
        for &dependency in &dependencies {
            self.jobs[dependency].dependents.push(position);
        }
        self.positions.insert(job_id.clone(), position);
        self.jobs.push(Job {
            id: job_id,
            tenant,
            priority,
            depends_on: dependencies,
            status: Status::Queued,
            not_before: 0,
            failures: 0,
            dependents: Vec::new(),
        });
        self.enqueue(position);
        true
    }

    // Level 4
    pub fn cancel(&mut self, timestamp: i64, job_id: String) -> i32 {
        let position = match self.positions.get(&job_id) {
            Some(&position) if self.jobs[position].status == Status::Queued => position,
            _ => return 0,
        };
        self.unqueue(position);
        self.jobs[position].status = Status::Cancelled;
        1 + self.cancel_dependents(position)
    }

    fn can_start(&self, position: usize, timestamp: i64) -> bool {
        let job = &self.jobs[position];
        if job.not_before > timestamp {
            return false;
        }
        if job
            .depends_on
            .iter()
            .any(|&dependency| self.jobs[dependency].status != Status::Done)
        {
            return false;
        }
        self.within_limit(&job.tenant, timestamp)
    }

    fn within_limit(&self, tenant: &str, timestamp: i64) -> bool {
        let Some(limit) = self.limits.get(tenant) else {
            return true;
        };
        let starts = self.starts.get(tenant).map_or(&[][..], Vec::as_slice);
        let window_start = timestamp - limit.window;
        let in_window = starts.len() - starts.partition_point(|&start| start <= window_start);
        in_window < limit.limit as usize
    }

    /// Cancels every queued job that waits, directly or not, on `position`; returns how many.
    fn cancel_dependents(&mut self, position: usize) -> i32 {
        let mut cancelled = 0;
        let mut pending = self.jobs[position].dependents.clone();
        while let Some(next) = pending.pop() {
            if self.jobs[next].status == Status::Queued {
                self.unqueue(next);
                self.jobs[next].status = Status::Cancelled;
                cancelled += 1;
                pending.extend_from_slice(&self.jobs[next].dependents);
            }
        }
        cancelled
    }

    /// Queue order: higher priority first, then earlier submission.
    fn order(&self, position: usize) -> (i64, usize) {
        (-i64::from(self.jobs[position].priority), position)
    }

    fn enqueue(&mut self, position: usize) {
        self.jobs[position].status = Status::Queued;
        let key = self.order(position);
        let spot = self
            .queue
            .partition_point(|&queued| self.order(queued) <= key);
        self.queue.insert(spot, position);
    }

    fn unqueue(&mut self, position: usize) {
        let key = self.order(position);
        let spot = self
            .queue
            .partition_point(|&queued| self.order(queued) <= key);
        self.queue.remove(spot - 1);
    }
}
