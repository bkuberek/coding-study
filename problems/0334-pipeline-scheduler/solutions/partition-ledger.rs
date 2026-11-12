use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap, HashSet, VecDeque};

const DONE: &str = "done";
const FAILED: &str = "failed";
const MISSING: &str = "missing";

type Part = (String, i32);

/// Tasks and their dependencies form a graph. The order counts the unlisted dependencies of each
/// task and keeps the ready names in a heap, so that the smallest ready name goes next.
///
/// A ledger keyed by (task, day) records each partition's state. Every write gets a number, and
/// the partition remembers the number of each input it read, which is all it takes to tell a
/// stale partition and to find what a backfill must rerun. Runs and backfills share one attempt
/// loop, which follows the scripted outcomes and the task's retries.
pub struct PipelineScheduler {
    tasks: Vec<String>,
    deps: HashMap<String, Vec<String>>,
    windows: HashMap<(String, String), i32>,
    retries: HashMap<String, i32>,
    scripts: HashMap<Part, VecDeque<String>>,
    state: HashMap<Part, &'static str>,
    written: HashMap<Part, i32>,
    reads: HashMap<Part, HashMap<Part, i32>>,
    writes: i32,
}

impl PipelineScheduler {
    pub fn new() -> Self {
        PipelineScheduler {
            tasks: Vec::new(),
            deps: HashMap::new(),
            windows: HashMap::new(),
            retries: HashMap::new(),
            scripts: HashMap::new(),
            state: HashMap::new(),
            written: HashMap::new(),
            reads: HashMap::new(),
            writes: 0,
        }
    }

    // Level 1
    pub fn add_task(&mut self, name: String, deps: Vec<String>) -> bool {
        if self.deps.contains_key(&name) {
            return false;
        }
        let mut unique: Vec<String> = Vec::new();
        for dep in deps {
            if !unique.contains(&dep) {
                unique.push(dep);
            }
        }
        self.tasks.push(name.clone());
        self.deps.insert(name, unique);
        true
    }

    pub fn validate(&mut self) -> Vec<Vec<String>> {
        let mut problems: Vec<Vec<String>> = Vec::new();
        for task in &self.tasks {
            for dep in &self.deps[task] {
                if !self.deps.contains_key(dep) {
                    problems.push(vec![
                        "unknown-dependency".to_string(),
                        task.clone(),
                        dep.clone(),
                    ]);
                }
            }
        }
        let listed: HashSet<String> = self.order().into_iter().collect();
        for task in &self.tasks {
            if !listed.contains(task) && self.reaches_itself(task) {
                problems.push(vec!["cycle".to_string(), task.clone()]);
            }
        }
        problems.sort();
        problems
    }

    pub fn run_order(&mut self) -> Vec<String> {
        if self.validate().is_empty() {
            self.order()
        } else {
            Vec::new()
        }
    }

    // Level 2
    pub fn set_window(&mut self, task: String, dep: String, days: i32) -> bool {
        if !self.deps.get(&task).is_some_and(|list| list.contains(&dep)) {
            return false;
        }
        self.windows.insert((task, dep), days);
        true
    }

    pub fn mark_done(&mut self, task: String, day: i32) {
        self.store(&task, day);
    }

    pub fn runnable(&mut self, day: i32) -> Vec<String> {
        let mut out: Vec<String> = self
            .tasks
            .iter()
            .filter(|task| {
                self.state_of(&((*task).clone(), day)) != DONE && self.inputs_done(task, day)
            })
            .cloned()
            .collect();
        out.sort();
        out
    }

    // Level 3
    pub fn set_retries(&mut self, task: String, retries: i32) {
        self.retries.insert(task, retries);
    }

    pub fn script(&mut self, task: String, day: i32, outcomes: Vec<String>) {
        self.scripts
            .insert((task, day), outcomes.into_iter().collect());
    }

    pub fn run(&mut self, day: i32) -> Vec<Vec<String>> {
        let mut rows = Vec::new();
        for task in self.run_order() {
            if !self.inputs_done(&task, day) {
                rows.push(vec![task, "skipped".to_string(), "0".to_string()]);
                continue;
            }
            let (attempts, succeeded) = self.attempt(&task, day);
            rows.push(vec![task, result(succeeded), attempts.to_string()]);
        }
        rows
    }

    pub fn status(&mut self, task: String, day: i32) -> String {
        self.state
            .get(&(task, day))
            .copied()
            .unwrap_or(MISSING)
            .to_string()
    }

    // Level 4
    pub fn stale(&mut self, day: i32) -> Vec<String> {
        let mut out: Vec<String> = self
            .tasks
            .iter()
            .filter(|task| self.is_stale(&((*task).clone(), day)))
            .cloned()
            .collect();
        out.sort();
        out
    }

    pub fn plan(&mut self, task: String, from_day: i32, to_day: i32) -> Vec<Vec<String>> {
        self.make_plan(&task, from_day, to_day)
            .into_iter()
            .map(|(name, day)| vec![day.to_string(), name])
            .collect()
    }

    pub fn backfill(
        &mut self,
        task: String,
        from_day: i32,
        to_day: i32,
        cap: i32,
    ) -> Vec<Vec<String>> {
        let plan = self.make_plan(&task, from_day, to_day);
        let planned: HashSet<Part> = plan.iter().cloned().collect();
        let mut results: HashMap<Part, (i32, String, i32)> = HashMap::new();
        let mut round = 0;
        while results.len() < plan.len() {
            round += 1;
            // Inputs come before their users in plan order, so one pass settles every skip.
            for p in &plan {
                if !results.contains_key(p) && self.blocked(p, &planned, &results) {
                    results.insert(p.clone(), (round, "skipped".to_string(), 0));
                }
            }
            let ready: Vec<Part> = plan
                .iter()
                .filter(|p| {
                    !results.contains_key(*p)
                        && self
                            .inputs(&p.0, p.1)
                            .iter()
                            .filter(|i| planned.contains(*i))
                            .all(|i| results.get(i).is_some_and(|r| r.1 == "success"))
                })
                .take(cap as usize)
                .cloned()
                .collect();
            for p in ready {
                let (attempts, succeeded) = self.attempt(&p.0, p.1);
                results.insert(p, (round, result(succeeded), attempts));
            }
        }
        let rank = self.rank();
        let mut decided = plan;
        decided.sort_by_key(|p| (results[p].0, p.1, rank[&p.0]));
        decided
            .into_iter()
            .map(|p| {
                let (r, status, attempts) = &results[&p];
                vec![
                    r.to_string(),
                    p.1.to_string(),
                    p.0.clone(),
                    status.clone(),
                    attempts.to_string(),
                ]
            })
            .collect()
    }

    // The graph
    fn users(&self) -> HashMap<String, Vec<String>> {
        let mut users: HashMap<String, Vec<String>> = HashMap::new();
        for task in &self.tasks {
            for dep in &self.deps[task] {
                if self.deps.contains_key(dep) {
                    users.entry(dep.clone()).or_default().push(task.clone());
                }
            }
        }
        users
    }

    fn order(&self) -> Vec<String> {
        let mut waiting: HashMap<&String, usize> = HashMap::new();
        let mut ready: BinaryHeap<Reverse<String>> = BinaryHeap::new();
        for task in &self.tasks {
            let count = self.deps[task]
                .iter()
                .filter(|d| self.deps.contains_key(*d))
                .count();
            waiting.insert(task, count);
            if count == 0 {
                ready.push(Reverse(task.clone()));
            }
        }
        let users = self.users();
        let mut order = Vec::new();
        while let Some(Reverse(task)) = ready.pop() {
            for user in users.get(&task).into_iter().flatten() {
                let left = waiting.get_mut(user).unwrap();
                *left -= 1;
                if *left == 0 {
                    ready.push(Reverse(user.clone()));
                }
            }
            order.push(task);
        }
        order
    }

    fn reaches_itself(&self, start: &String) -> bool {
        let known = |list: &Vec<String>| -> Vec<String> {
            list.iter()
                .filter(|d| self.deps.contains_key(*d))
                .cloned()
                .collect()
        };
        let mut seen: HashSet<String> = HashSet::new();
        let mut stack = known(&self.deps[start]);
        while let Some(task) = stack.pop() {
            if &task == start {
                return true;
            }
            if seen.insert(task.clone()) {
                stack.extend(known(&self.deps[&task]));
            }
        }
        false
    }

    fn rank(&mut self) -> HashMap<String, usize> {
        self.run_order()
            .into_iter()
            .enumerate()
            .map(|(i, name)| (name, i))
            .collect()
    }

    // The partitions
    fn width(&self, task: &str, dep: &str) -> i32 {
        *self
            .windows
            .get(&(task.to_string(), dep.to_string()))
            .unwrap_or(&1)
    }

    fn inputs(&self, task: &str, day: i32) -> Vec<Part> {
        let mut inputs = Vec::new();
        for dep in &self.deps[task] {
            for d in (day - self.width(task, dep) + 1).max(0)..=day {
                inputs.push((dep.clone(), d));
            }
        }
        inputs
    }

    fn state_of(&self, p: &Part) -> &'static str {
        self.state.get(p).copied().unwrap_or(MISSING)
    }

    fn current(&self, p: &Part) -> i32 {
        if self.state_of(p) == DONE {
            self.written[p]
        } else {
            0
        }
    }

    fn inputs_done(&self, task: &str, day: i32) -> bool {
        self.inputs(task, day)
            .iter()
            .all(|p| self.state_of(p) == DONE)
    }

    fn store(&mut self, task: &str, day: i32) {
        self.writes += 1;
        let p = (task.to_string(), day);
        let seen: HashMap<Part, i32> = self
            .inputs(task, day)
            .into_iter()
            .map(|input| {
                let number = self.current(&input);
                (input, number)
            })
            .collect();
        self.state.insert(p.clone(), DONE);
        self.written.insert(p.clone(), self.writes);
        self.reads.insert(p, seen);
    }

    fn attempt(&mut self, task: &str, day: i32) -> (i32, bool) {
        let p = (task.to_string(), day);
        let limit = 1 + self.retries.get(task).copied().unwrap_or(0);
        for attempt in 1..=limit {
            let next = self
                .scripts
                .get_mut(&p)
                .and_then(|script| script.pop_front())
                .unwrap_or_else(|| "ok".to_string());
            if next == "ok" {
                self.store(task, day);
                return (attempt, true);
            }
        }
        self.state.insert(p, FAILED);
        (limit, false)
    }

    fn is_stale(&self, p: &Part) -> bool {
        self.state_of(p) == DONE
            && self.reads[p]
                .iter()
                .any(|(input, seen)| self.current(input) != *seen)
    }

    fn make_plan(&mut self, task: &str, from_day: i32, to_day: i32) -> Vec<Part> {
        let users = self.users();
        let mut planned: HashSet<Part> =
            (from_day..=to_day).map(|d| (task.to_string(), d)).collect();
        let mut frontier: Vec<Part> = planned.iter().cloned().collect();
        while let Some((upstream, day)) = frontier.pop() {
            for user in users.get(&upstream).into_iter().flatten() {
                for later in day..day + self.width(user, &upstream) {
                    let next = (user.clone(), later);
                    if self.state_of(&next) == DONE && planned.insert(next.clone()) {
                        frontier.push(next);
                    }
                }
            }
        }
        let rank = self.rank();
        let mut plan: Vec<Part> = planned.into_iter().collect();
        plan.sort_by_key(|p| (p.1, rank[&p.0]));
        plan
    }

    fn blocked(
        &self,
        p: &Part,
        planned: &HashSet<Part>,
        results: &HashMap<Part, (i32, String, i32)>,
    ) -> bool {
        self.inputs(&p.0, p.1).iter().any(|input| {
            if planned.contains(input) {
                results.get(input).is_some_and(|r| r.1 != "success")
            } else {
                self.state_of(input) != DONE
            }
        })
    }
}

fn result(succeeded: bool) -> String {
    if succeeded { "success" } else { "failed" }.to_string()
}
