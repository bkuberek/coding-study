use std::collections::{HashMap, HashSet};

const COUNTED: [&str; 4] = ["ok", "changed", "failed", "skipped"];

#[derive(Clone, Default)]
struct Host {
    files: HashMap<String, String>,
    packages: HashMap<String, String>,
    facts: HashMap<String, String>,
}

#[derive(Clone)]
struct Action {
    name: String,
    kind: String,
    target: String,
    value: String,
}

fn is_whole(text: &str) -> bool {
    let digits = text.strip_prefix('-').unwrap_or(text);
    !digits.is_empty() && digits.bytes().all(|b| b.is_ascii_digit())
}

/// The truth of one condition, or None when it cannot be decided.
fn compare(fact: &str, operator: &str, value: &str) -> Option<bool> {
    match operator {
        "==" => return Some(fact == value),
        "!=" => return Some(fact != value),
        _ => {}
    }
    if !is_whole(fact) || !is_whole(value) {
        return None;
    }
    let left: i64 = fact.parse().ok()?;
    let right: i64 = value.parse().ok()?;
    Some(match operator {
        "<" => left < right,
        "<=" => left <= right,
        ">" => left > right,
        _ => left >= right,
    })
}

/// The state a task of this kind compares with, or None for a missing service.
fn current(host: &Host, kind: &str, target: &str) -> Option<String> {
    match kind {
        "file" => Some(host.files.get(target).cloned().unwrap_or_default()),
        "package" => Some(if host.packages.contains_key(target) { "present" } else { "absent" }.to_string()),
        _ => host.packages.get(target).cloned(),
    }
}

fn apply(host: &mut Host, kind: &str, target: &str, value: &str) {
    match (kind, value) {
        ("file", _) => {
            host.files.insert(target.to_string(), value.to_string());
        }
        ("package", "present") => {
            host.packages.entry(target.to_string()).or_insert_with(|| "stopped".to_string());
        }
        ("package", _) => {
            host.packages.remove(target);
        }
        (_, "restarted") => {
            host.packages.insert(target.to_string(), "running".to_string());
        }
        _ => {
            host.packages.insert(target.to_string(), value.to_string());
        }
    }
}

fn change(host: &mut Host, action: &Action) -> (&'static str, Vec<String>) {
    let Some(before) = current(host, &action.kind, &action.target) else {
        return ("failed", Vec::new());
    };
    if before == action.value && action.value != "restarted" {
        return ("ok", Vec::new());
    }
    apply(host, &action.kind, &action.target, &action.value);
    ("changed", vec![before, action.value.clone()])
}

/// Tasks describe the state a host should be in. Running a task compares that state with the
/// host's and changes the host only when they differ, so a second run finds nothing to do. A run
/// works through the hosts in batches; in each batch it applies every task to every host still
/// standing, then the handlers that a change notified. A check run does the same on clones of the
/// hosts, so later tasks see what earlier ones would have done while the real hosts stay as they
/// were.
pub struct Converger {
    order: Vec<String>,
    hosts: HashMap<String, Host>,
    tasks: Vec<Action>,
    handlers: Vec<Action>,
    links: HashMap<String, Vec<String>>,
    conditions: HashMap<String, Vec<Action>>,
    batch: i32,
    counts: HashMap<String, HashMap<&'static str, usize>>,
}

impl Converger {
    pub fn new() -> Self {
        Converger {
            order: Vec::new(),
            hosts: HashMap::new(),
            tasks: Vec::new(),
            handlers: Vec::new(),
            links: HashMap::new(),
            conditions: HashMap::new(),
            batch: 0,
            counts: HashMap::new(),
        }
    }

    // Level 1
    pub fn add_host(&mut self, host: String) -> bool {
        if self.hosts.contains_key(&host) {
            return false;
        }
        self.hosts.insert(host.clone(), Host::default());
        self.order.push(host);
        true
    }

    pub fn set_state(&mut self, host: String, kind: String, target: String, value: String) -> bool {
        match self.hosts.get_mut(&host) {
            Some(found) => {
                apply(found, &kind, &target, &value);
                true
            }
            None => false,
        }
    }

    pub fn add_task(&mut self, name: String, kind: String, target: String, value: String) -> bool {
        if self.tasks.iter().any(|task| task.name == name) {
            return false;
        }
        self.tasks.push(Action { name, kind, target, value });
        true
    }

    pub fn run(&mut self) -> Vec<Vec<String>> {
        let mut hosts = std::mem::take(&mut self.hosts);
        let mut tally = HashMap::new();
        let rows = self.play(&mut hosts, false, &mut tally);
        self.hosts = hosts;
        self.counts = tally;
        rows
    }

    pub fn state(&mut self, host: String) -> Vec<Vec<String>> {
        let Some(found) = self.hosts.get(&host) else {
            return Vec::new();
        };
        let mut rows: Vec<Vec<String>> =
            found.files.iter().map(|(path, content)| vec!["file".to_string(), path.clone(), content.clone()]).collect();
        for (name, service) in &found.packages {
            rows.push(vec!["package".to_string(), name.clone(), "present".to_string()]);
            rows.push(vec!["service".to_string(), name.clone(), service.clone()]);
        }
        rows.sort_by(|a, b| (&a[0], &a[1]).cmp(&(&b[0], &b[1])));
        rows
    }

    // Level 2
    pub fn check(&mut self) -> Vec<Vec<String>> {
        let mut copies = self.hosts.clone();
        let mut tally = HashMap::new();
        self.play(&mut copies, true, &mut tally)
    }

    // Level 3
    pub fn add_handler(&mut self, name: String, kind: String, target: String, value: String) -> bool {
        if self.handlers.iter().any(|handler| handler.name == name) {
            return false;
        }
        self.handlers.push(Action { name, kind, target, value });
        true
    }

    pub fn notifies(&mut self, task: String, handler: String) -> bool {
        let known_task = self.tasks.iter().any(|t| t.name == task);
        let known_handler = self.handlers.iter().any(|h| h.name == handler);
        if !known_task || !known_handler {
            return false;
        }
        let linked = self.links.entry(task).or_default();
        if linked.contains(&handler) {
            return false;
        }
        linked.push(handler);
        true
    }

    // Level 4
    pub fn set_fact(&mut self, host: String, key: String, value: String) -> bool {
        match self.hosts.get_mut(&host) {
            Some(found) => found.facts.insert(key, value).is_none(),
            None => false,
        }
    }

    pub fn only_if(&mut self, task: String, fact: String, comparison: String, value: String) -> bool {
        if !self.tasks.iter().any(|t| t.name == task) {
            return false;
        }
        let condition = Action { name: fact, kind: comparison, target: value, value: String::new() };
        self.conditions.entry(task).or_default().push(condition);
        true
    }

    pub fn set_batch_size(&mut self, size: i32) -> bool {
        let changed = size != self.batch;
        self.batch = size;
        changed
    }

    pub fn summary(&mut self) -> Vec<Vec<String>> {
        self.order
            .iter()
            .map(|host| {
                let mut row = vec![host.clone()];
                for status in COUNTED {
                    let count = self.counts.get(host).and_then(|t| t.get(status)).copied().unwrap_or(0);
                    row.push(count.to_string());
                }
                row
            })
            .collect()
    }

    // Running
    fn play(
        &self,
        hosts: &mut HashMap<String, Host>,
        dry: bool,
        tally: &mut HashMap<String, HashMap<&'static str, usize>>,
    ) -> Vec<Vec<String>> {
        let size = if self.batch > 0 { self.batch as usize } else { self.order.len().max(1) };
        let mut rows = Vec::new();
        let mut record = |host: &str, step: &str, status: &'static str, diff: Vec<String>| {
            *tally.entry(host.to_string()).or_default().entry(status).or_insert(0) += 1;
            let mut row = vec![host.to_string(), step.to_string(), status.to_string()];
            if dry {
                row.extend(diff);
            }
            rows.push(row);
        };
        for group in self.order.chunks(size) {
            let mut failed: HashSet<&String> = HashSet::new();
            let mut notified: HashMap<&String, HashSet<&String>> =
                group.iter().map(|host| (host, HashSet::new())).collect();
            for task in &self.tasks {
                for host in group {
                    if failed.contains(host) {
                        continue;
                    }
                    let found = hosts.get_mut(host).unwrap();
                    let (status, diff) = self.task(found, task);
                    if status == "failed" {
                        failed.insert(host);
                    } else if status == "changed" {
                        if let Some(linked) = self.links.get(&task.name) {
                            notified.get_mut(host).unwrap().extend(linked.iter());
                        }
                    }
                    record(host, &task.name, status, diff);
                }
            }
            for handler in &self.handlers {
                for host in group {
                    if failed.contains(host) || !notified[host].contains(&handler.name) {
                        continue;
                    }
                    let (status, diff) = change(hosts.get_mut(host).unwrap(), handler);
                    if status == "failed" {
                        failed.insert(host);
                    }
                    record(host, &handler.name, status, diff);
                }
            }
            if failed.len() == group.len() {
                break;
            }
        }
        rows
    }

    fn task(&self, host: &mut Host, task: &Action) -> (&'static str, Vec<String>) {
        for condition in self.conditions.get(&task.name).into_iter().flatten() {
            let Some(have) = host.facts.get(&condition.name) else {
                return ("failed", Vec::new());
            };
            match compare(have, &condition.kind, &condition.target) {
                None => return ("failed", Vec::new()),
                Some(false) => return ("skipped", Vec::new()),
                Some(true) => {}
            }
        }
        change(host, task)
    }
}
