use std::collections::{HashMap, VecDeque};

/// One CPU's record of a run: its segments, the last process it ran, its switches and the ticks
/// it was busy.
#[derive(Default)]
struct Core {
    segments: Vec<(String, i32, i32)>,
    last: Option<String>,
    switches: i32,
    busy: i32,
}

impl Core {
    fn run(&mut self, pid: &str, start: i32, end: i32) {
        let continues = matches!(self.segments.last(), Some(tail) if tail.0 == pid && tail.2 == start);
        if continues {
            if let Some(tail) = self.segments.last_mut() {
                tail.2 = end;
            }
        } else {
            if self.last.as_deref().is_some_and(|last| last != pid) {
                self.switches += 1;
            }
            self.segments.push((pid.to_string(), start, end));
        }
        self.last = Some(pid.to_string());
        self.busy += end - start;
    }
}

/// The result of the latest run: when each process first ran and finished, and the cores.
struct Run {
    pids: Vec<String>,
    first: HashMap<String, i32>,
    done: HashMap<String, i32>,
    cores: Vec<Core>,
    migrations: i32,
    makespan: i32,
}

impl Run {
    fn new(pids: &[String], cores: usize) -> Self {
        Run {
            pids: pids.to_vec(),
            first: HashMap::new(),
            done: HashMap::new(),
            cores: (0..cores).map(|_| Core::default()).collect(),
            migrations: 0,
            makespan: 0,
        }
    }

    fn started(&mut self, pid: &str, time: i32) {
        self.first.entry(pid.to_string()).or_insert(time);
    }

    fn timelines(&self) -> Vec<Vec<String>> {
        self.cores
            .iter()
            .map(|core| {
                core.segments
                    .iter()
                    .map(|(pid, start, end)| format!("{pid}:{start}-{end}"))
                    .collect()
            })
            .collect()
    }
}

fn fraction(numerator: i32, denominator: i32) -> String {
    let (mut a, mut b) = (numerator, denominator);
    while b != 0 {
        (a, b) = (b, a % b);
    }
    format!("{}/{}", numerator / a, denominator / a)
}

/// A workload of processes and the result of the latest run over it.
///
/// First come, first served and shortest job first run each process to completion, so they jump
/// from one completion to the next. Round robin, the feedback queue and the cores advance a clock
/// one tick at a time and settle each tick in the order the statement fixes: the slice that ends,
/// the arrivals, the process that goes back to its queue, a boost, a preemption, a dispatch and
/// then a steal. One core records its segments, merging a slice that continues the one before.
/// Round robin is the case of one core without stealing.
pub struct CpuScheduler {
    pids: Vec<String>,
    arrival: HashMap<String, i32>,
    burst: HashMap<String, i32>,
    latest: Option<Run>,
}

impl CpuScheduler {
    pub fn new() -> Self {
        CpuScheduler {
            pids: Vec::new(),
            arrival: HashMap::new(),
            burst: HashMap::new(),
            latest: None,
        }
    }

    // Level 1
    pub fn add_process(&mut self, pid: String, arrival: i32, burst: i32) -> bool {
        if self.arrival.contains_key(&pid) {
            return false;
        }
        self.arrival.insert(pid.clone(), arrival);
        self.burst.insert(pid.clone(), burst);
        self.pids.push(pid);
        true
    }

    pub fn run_fcfs(&mut self) -> Vec<String> {
        let mut run = Run::new(&self.pids, 1);
        let mut clock = 0;
        for pid in self.by_arrival() {
            let start = clock.max(self.arrival[&pid]);
            clock = self.run_to_completion(&mut run, &pid, start);
        }
        self.keep(run, clock).swap_remove(0)
    }

    pub fn run_sjf(&mut self) -> Vec<String> {
        let mut run = Run::new(&self.pids, 1);
        let position: HashMap<&str, usize> =
            self.pids.iter().enumerate().map(|(i, pid)| (pid.as_str(), i)).collect();
        let key = |pid: &str| (self.burst[pid], self.arrival[pid], position[pid]);
        let mut pending: Vec<String> = self.pids.clone();
        let mut clock = 0;
        while !pending.is_empty() {
            let pick = (0..pending.len())
                .filter(|&i| self.arrival[&pending[i]] <= clock)
                .min_by_key(|&i| key(pending[i].as_str()));
            match pick {
                None => clock = pending.iter().map(|pid| self.arrival[pid]).min().unwrap(),
                Some(i) => {
                    let pid = pending.remove(i);
                    clock = self.run_to_completion(&mut run, &pid, clock);
                }
            }
        }
        self.keep(run, clock).swap_remove(0)
    }

    pub fn waiting_time(&mut self, pid: String) -> i32 {
        match self.turnaround_time(pid.clone()) {
            -1 => -1,
            turnaround => turnaround - self.burst[&pid],
        }
    }

    pub fn turnaround_time(&mut self, pid: String) -> i32 {
        match self.latest.as_ref().and_then(|run| run.done.get(&pid)) {
            Some(done) => done - self.arrival[&pid],
            None => -1,
        }
    }

    pub fn average_waiting(&mut self) -> String {
        self.average(|s, pid| s.waiting_time(pid.to_string()))
    }

    pub fn average_turnaround(&mut self) -> String {
        self.average(|s, pid| s.turnaround_time(pid.to_string()))
    }

    // Level 2
    pub fn run_round_robin(&mut self, quantum: i32) -> Vec<String> {
        self.round_robin(1, quantum, false).swap_remove(0)
    }

    pub fn response_time(&mut self, pid: String) -> i32 {
        match self.latest.as_ref().and_then(|run| run.first.get(&pid)) {
            Some(first) => first - self.arrival[&pid],
            None => -1,
        }
    }

    pub fn average_response(&mut self) -> String {
        self.average(|s, pid| s.response_time(pid.to_string()))
    }

    pub fn context_switches(&mut self) -> i32 {
        match &self.latest {
            Some(run) => run.cores.iter().map(|core| core.switches).sum(),
            None => -1,
        }
    }

    // Level 3
    pub fn run_mlfq(&mut self, quanta: Vec<i32>, boost_period: i32) -> Vec<String> {
        let mut run = Run::new(&self.pids, 1);
        let mut remaining = self.burst.clone();
        let mut arrivals: VecDeque<String> = self.by_arrival().into();
        let mut queues: Vec<VecDeque<String>> = vec![VecDeque::new(); quanta.len()];
        let mut level: HashMap<String, usize> = HashMap::new();
        let mut used: HashMap<String, i32> = HashMap::new();
        let mut running: Option<String> = None;
        let mut left = self.pids.len();
        let mut clock = 0;
        loop {
            let mut demoted = None;
            if let Some(pid) = running.take() {
                if remaining[&pid] == 0 {
                    run.done.insert(pid, clock);
                    left -= 1;
                } else if used[&pid] == quanta[level[&pid]] {
                    level.insert(pid.clone(), (level[&pid] + 1).min(quanta.len() - 1));
                    used.insert(pid.clone(), 0);
                    demoted = Some(pid);
                } else {
                    running = Some(pid);
                }
            }
            if left == 0 {
                break;
            }
            while arrivals.front().is_some_and(|pid| self.arrival[pid] == clock) {
                let pid = arrivals.pop_front().unwrap();
                level.insert(pid.clone(), 0);
                used.insert(pid.clone(), 0);
                queues[0].push_back(pid);
            }
            if let Some(pid) = demoted {
                queues[level[&pid]].push_back(pid);
            }
            if boost_period > 0 && clock > 0 && clock % boost_period == 0 {
                let merged: VecDeque<String> = queues.iter_mut().flat_map(|q| q.drain(..)).collect();
                for pid in merged.iter().chain(running.iter()) {
                    level.insert(pid.clone(), 0);
                    used.insert(pid.clone(), 0);
                }
                queues[0] = merged;
            }
            if let Some(pid) = running.take() {
                let mine = level[&pid];
                if queues[..mine].iter().any(|q| !q.is_empty()) {
                    queues[mine].push_back(pid);
                } else {
                    running = Some(pid);
                }
            }
            if running.is_none() {
                running = queues.iter_mut().find(|q| !q.is_empty()).and_then(|q| q.pop_front());
            }
            if let Some(pid) = &running {
                run.started(pid, clock);
                run.cores[0].run(pid, clock, clock + 1);
                *remaining.get_mut(pid).unwrap() -= 1;
                *used.get_mut(pid).unwrap() += 1;
            }
            clock += 1;
        }
        self.keep(run, clock).swap_remove(0)
    }

    // Level 4
    pub fn run_multicore(&mut self, cores: i32, quantum: i32, steal: bool) -> Vec<Vec<String>> {
        self.round_robin(cores as usize, quantum, steal)
    }

    pub fn utilization(&mut self, core: i32) -> String {
        match &self.latest {
            Some(run) if core >= 0 && (core as usize) < run.cores.len() => {
                fraction(run.cores[core as usize].busy, run.makespan)
            }
            _ => String::new(),
        }
    }

    pub fn migrations(&mut self) -> i32 {
        self.latest.as_ref().map_or(-1, |run| run.migrations)
    }

    // The clock loops
    fn round_robin(&mut self, cores: usize, quantum: i32, steal: bool) -> Vec<Vec<String>> {
        let mut run = Run::new(&self.pids, cores);
        let mut remaining = self.burst.clone();
        let mut arrivals: VecDeque<String> = self.by_arrival().into();
        let mut queues: Vec<VecDeque<String>> = vec![VecDeque::new(); cores];
        let mut running: Vec<Option<String>> = vec![None; cores];
        let mut used = vec![0; cores];
        let mut left = self.pids.len();
        let mut clock = 0;
        loop {
            let mut expired: Vec<Option<String>> = vec![None; cores];
            for c in 0..cores {
                if let Some(pid) = running[c].take() {
                    if remaining[&pid] == 0 {
                        run.done.insert(pid, clock);
                        left -= 1;
                    } else if used[c] == quantum {
                        expired[c] = Some(pid);
                    } else {
                        running[c] = Some(pid);
                    }
                }
            }
            if left == 0 {
                break;
            }
            while arrivals.front().is_some_and(|pid| self.arrival[pid] == clock) {
                let load = |c: usize| {
                    queues[c].len() + usize::from(running[c].is_some()) + usize::from(expired[c].is_some())
                };
                let target = (0..cores).min_by_key(|&c| (load(c), c)).unwrap();
                queues[target].push_back(arrivals.pop_front().unwrap());
            }
            for c in 0..cores {
                if let Some(pid) = expired[c].take() {
                    queues[c].push_back(pid);
                }
                if running[c].is_none() {
                    if let Some(pid) = queues[c].pop_front() {
                        running[c] = Some(pid);
                        used[c] = 0;
                    }
                }
            }
            if steal {
                for c in 0..cores {
                    if running[c].is_some() {
                        continue;
                    }
                    let victim = (0..cores).max_by_key(|&v| (queues[v].len(), std::cmp::Reverse(v))).unwrap();
                    if let Some(pid) = queues[victim].pop_back() {
                        running[c] = Some(pid);
                        used[c] = 0;
                        run.migrations += 1;
                    }
                }
            }
            for c in 0..cores {
                if let Some(pid) = &running[c] {
                    run.started(pid, clock);
                    run.cores[c].run(pid, clock, clock + 1);
                    *remaining.get_mut(pid).unwrap() -= 1;
                    used[c] += 1;
                }
            }
            clock += 1;
        }
        self.keep(run, clock)
    }

    fn run_to_completion(&self, run: &mut Run, pid: &str, start: i32) -> i32 {
        let end = start + self.burst[pid];
        run.started(pid, start);
        run.cores[0].run(pid, start, end);
        run.done.insert(pid.to_string(), end);
        end
    }

    fn by_arrival(&self) -> Vec<String> {
        let mut order = self.pids.clone();
        order.sort_by_key(|pid| self.arrival[pid]);
        order
    }

    fn keep(&mut self, mut run: Run, makespan: i32) -> Vec<Vec<String>> {
        run.makespan = makespan;
        let lines = run.timelines();
        self.latest = Some(run);
        lines
    }

    fn average(&mut self, metric: impl Fn(&mut Self, &str) -> i32) -> String {
        let pids = match &self.latest {
            Some(run) => run.pids.clone(),
            None => return String::new(),
        };
        let total: i32 = pids.iter().map(|pid| metric(self, pid)).sum();
        fraction(total, pids.len() as i32)
    }
}
