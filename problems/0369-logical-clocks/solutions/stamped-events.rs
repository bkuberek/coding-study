use std::collections::{HashMap, HashSet};

#[derive(Clone)]
struct Stamp {
    process: usize,
    lamport: i32,
    vector: Vec<i32>,
    l: i64,
    c: i64,
    wall: i64,
    is_send: bool,
    value: String,
}

fn at_most(first: &[i32], second: &[i32]) -> bool {
    first.iter().zip(second).all(|(a, b)| a <= b)
}

/// The update of Kulkarni et al.: `l` is the largest physical reading heard of, and `c` counts
/// the events since `l` last changed.
fn next_hybrid(current: (i64, i64), wall: i64, sent: Option<&Stamp>) -> (i64, i64) {
    let (old_l, old_c) = current;
    match sent {
        None => {
            let l = old_l.max(wall);
            (l, if l == old_l { old_c + 1 } else { 0 })
        }
        Some(message) => {
            let l = old_l.max(message.l).max(wall);
            if l == old_l && l == message.l {
                (l, old_c.max(message.c) + 1)
            } else if l == old_l {
                (l, old_c + 1)
            } else if l == message.l {
                (l, message.c + 1)
            } else {
                (l, 0)
            }
        }
    }
}

/// Each process keeps the current value of its three clocks: a Lamport counter, a vector and a
/// hybrid pair. Every event updates them by the rules of its kind and keeps a copy as its stamp,
/// so every question afterwards is answered from the stamps alone.
pub struct LogicalClocks {
    processes: usize,
    lamport_now: Vec<i32>,
    vector_now: Vec<Vec<i32>>,
    hybrid_now: Vec<(i64, i64)>,
    events: HashMap<String, Stamp>,
    received: HashSet<String>,
    writes: HashMap<String, Vec<String>>,
}

impl LogicalClocks {
    pub fn new(processes: i32) -> Self {
        let size = processes as usize;
        LogicalClocks {
            processes: size,
            lamport_now: vec![0; size],
            vector_now: vec![vec![0; size]; size],
            hybrid_now: vec![(0, 0); size],
            events: HashMap::new(),
            received: HashSet::new(),
            writes: HashMap::new(),
        }
    }

    // Level 1
    pub fn local(&mut self, process: i32, event: String, wall: i64) -> i32 {
        self.record(process, event, wall, None, false)
    }

    pub fn send(&mut self, process: i32, event: String, wall: i64) -> i32 {
        self.record(process, event, wall, None, true)
    }

    pub fn receive(&mut self, process: i32, event: String, message: String, wall: i64) -> i32 {
        let sent = match self.events.get(&message) {
            Some(found) => found.clone(),
            None => return -1,
        };
        if !sent.is_send || self.received.contains(&message) || sent.process as i32 == process {
            return -1;
        }
        let result = self.record(process, event, wall, Some(&sent), false);
        if result != -1 {
            self.received.insert(message);
        }
        result
    }

    pub fn total_order(&mut self) -> Vec<String> {
        self.sorted_by(|found| (found.lamport, found.process))
    }

    // Level 2
    pub fn vector(&mut self, event: String) -> Vec<i32> {
        self.events.get(&event).map(|found| found.vector.clone()).unwrap_or_default()
    }

    pub fn compare(&mut self, first: String, second: String) -> String {
        let answer = match (self.events.get(&first), self.events.get(&second)) {
            (Some(one), Some(other)) => {
                if first == second {
                    "same"
                } else if at_most(&one.vector, &other.vector) {
                    "before"
                } else if at_most(&other.vector, &one.vector) {
                    "after"
                } else {
                    "concurrent"
                }
            }
            _ => "",
        };
        answer.to_string()
    }

    // Level 3
    pub fn write(&mut self, process: i32, event: String, key: String, value: String, wall: i64) -> i32 {
        let result = self.record(process, event.clone(), wall, None, false);
        if result != -1 {
            self.events.get_mut(&event).unwrap().value = value;
            self.writes.entry(key).or_default().push(event);
        }
        result
    }

    pub fn read(&mut self, process: i32, key: String) -> Vec<String> {
        if process < 0 || process as usize >= self.processes {
            return Vec::new();
        }
        let now = &self.vector_now[process as usize];
        let known: Vec<&Stamp> = self
            .writes
            .get(&key)
            .map(|names| names.iter().map(|name| &self.events[name]).collect())
            .unwrap_or_default();
        let known: Vec<&Stamp> = known.into_iter().filter(|found| at_most(&found.vector, now)).collect();
        // Two different events never share a vector, so `<=` and not equal means "happened before".
        let mut values: Vec<String> = known
            .iter()
            .filter(|found| {
                !known
                    .iter()
                    .any(|other| other.vector != found.vector && at_most(&found.vector, &other.vector))
            })
            .map(|found| found.value.clone())
            .collect();
        values.sort();
        values
    }

    pub fn concurrent_writes(&mut self, key: String) -> Vec<Vec<String>> {
        let mut names = self.writes.get(&key).cloned().unwrap_or_default();
        names.sort();
        let mut pairs = Vec::new();
        for i in 0..names.len() {
            for j in i + 1..names.len() {
                if self.compare(names[i].clone(), names[j].clone()) == "concurrent" {
                    pairs.push(vec![names[i].clone(), names[j].clone()]);
                }
            }
        }
        pairs
    }

    // Level 4
    pub fn hlc(&mut self, event: String) -> Vec<i64> {
        self.events.get(&event).map(|found| vec![found.l, found.c]).unwrap_or_default()
    }

    pub fn hlc_order(&mut self) -> Vec<String> {
        self.sorted_by(|found| (found.l, found.c, found.process))
    }

    pub fn max_offset(&mut self) -> i64 {
        self.events.values().map(|found| found.l - found.wall).max().unwrap_or(0)
    }

    // Shared
    fn sorted_by<K: Ord>(&self, sort_key: impl Fn(&Stamp) -> K) -> Vec<String> {
        let mut names: Vec<String> = self.events.keys().cloned().collect();
        names.sort_by_key(|name| sort_key(&self.events[name]));
        names
    }

    fn record(&mut self, process: i32, event: String, wall: i64, sent: Option<&Stamp>, is_send: bool) -> i32 {
        if process < 0 || process as usize >= self.processes || self.events.contains_key(&event) {
            return -1;
        }
        let at = process as usize;
        let mut lamport = self.lamport_now[at];
        let mut vector = self.vector_now[at].clone();
        match sent {
            None => lamport += 1,
            Some(message) => {
                lamport = lamport.max(message.lamport) + 1;
                for (mine, theirs) in vector.iter_mut().zip(&message.vector) {
                    *mine = (*mine).max(*theirs);
                }
            }
        }
        vector[at] += 1;
        let (l, c) = next_hybrid(self.hybrid_now[at], wall, sent);
        self.lamport_now[at] = lamport;
        self.vector_now[at] = vector.clone();
        self.hybrid_now[at] = (l, c);
        self.events.insert(
            event,
            Stamp { process: at, lamport, vector, l, c, wall, is_send, value: String::new() },
        );
        lamport
    }
}
