use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap};

const UNKNOWN: &str = "!unknown";
const UNEXPECTED: &str = "!unexpected";

fn fits(pattern: &[String], args: &[String]) -> bool {
    pattern.len() == args.len() && pattern.iter().zip(args).all(|(p, a)| p == "*" || p == a)
}

struct Rule {
    pattern: Vec<String>,
    answers: Vec<String>,
    used: usize,
}

struct Expectation {
    method: String,
    pattern: Vec<String>,
    answer: String,
    times: i32,
    used: i32,
}

struct Double {
    mock: bool,
    strict: bool,
    rules: HashMap<String, Vec<Rule>>,
    fallback: HashMap<String, String>,
    expectations: Vec<Expectation>,
    unexpected: Vec<(String, Vec<String>)>,
    calls: Vec<usize>,
}

impl Double {
    fn new(mock: bool, strict: bool) -> Self {
        Double {
            mock,
            strict,
            rules: HashMap::new(),
            fallback: HashMap::new(),
            expectations: Vec::new(),
            unexpected: Vec::new(),
            calls: Vec::new(),
        }
    }

    fn answer(&mut self, method: &str, args: &[String]) -> String {
        for e in self.expectations.iter_mut() {
            if e.method == method && e.used < e.times && fits(&e.pattern, args) {
                e.used += 1;
                return e.answer.clone();
            }
        }
        if let Some(rules) = self.rules.get_mut(method) {
            if let Some(rule) = rules.iter_mut().rev().find(|rule| fits(&rule.pattern, args)) {
                let answer = rule.answers[rule.used.min(rule.answers.len() - 1)].clone();
                rule.used += 1;
                return answer;
            }
        }
        if let Some(answer) = self.fallback.get(method) {
            return answer.clone();
        }
        if !self.mock {
            return String::new();
        }
        self.unexpected.push((method.to_string(), args.to_vec()));
        if self.strict { UNEXPECTED.to_string() } else { String::new() }
    }
}

struct LoggedCall {
    name: String,
    method: String,
    args: Vec<String>,
    time: i64,
}

struct Timer {
    name: String,
    method: String,
    args: Vec<String>,
    interval: i64,
    stopped: bool,
}

/// Every double keeps its stub rules per method, newest last, and a mock also keeps its
/// expectations in the order they were set. One log holds every call in the order it was made,
/// with its time, and each double keeps the positions of its own calls in that log, so the spy
/// questions read short lists. A list of names keeps the order the doubles were made in. Timers
/// wait in a min-heap ordered by due time, then by the sequence number they got when they were
/// last put in, so equal times fire in scheduling order.
pub struct Doubles {
    doubles: HashMap<String, Double>,
    order: Vec<String>,
    log: Vec<LoggedCall>,
    clock: i64,
    timers: Vec<Timer>,
    heap: BinaryHeap<Reverse<(i64, i64, usize)>>,
    sequence: i64,
}

impl Doubles {
    pub fn new() -> Self {
        Doubles {
            doubles: HashMap::new(),
            order: Vec::new(),
            log: Vec::new(),
            clock: 0,
            timers: Vec::new(),
            heap: BinaryHeap::new(),
            sequence: 0,
        }
    }

    // Level 1
    pub fn add_stub(&mut self, name: String) -> bool {
        self.add(name, false, false)
    }

    pub fn on_call(
        &mut self,
        name: String,
        method: String,
        args: Vec<String>,
        answers: Vec<String>,
    ) -> bool {
        match self.doubles.get_mut(&name) {
            None => false,
            Some(double) => {
                double.rules.entry(method).or_default().push(Rule { pattern: args, answers, used: 0 });
                true
            }
        }
    }

    pub fn otherwise(&mut self, name: String, method: String, answer: String) -> bool {
        match self.doubles.get_mut(&name) {
            None => false,
            Some(double) => {
                double.fallback.insert(method, answer);
                true
            }
        }
    }

    pub fn call(&mut self, name: String, method: String, args: Vec<String>) -> String {
        let position = self.log.len();
        match self.doubles.get_mut(&name) {
            None => UNKNOWN.to_string(),
            Some(double) => {
                double.calls.push(position);
                let answer = double.answer(&method, &args);
                self.log.push(LoggedCall { name, method, args, time: self.clock });
                answer
            }
        }
    }

    // Level 2
    pub fn call_count(&mut self, name: String, method: String) -> i32 {
        self.count(&name, &method, None)
    }

    pub fn match_count(&mut self, name: String, method: String, args: Vec<String>) -> i32 {
        self.count(&name, &method, Some(&args))
    }

    pub fn nth_call(&mut self, name: String, n: i32) -> Vec<String> {
        let calls = match self.doubles.get(&name) {
            None => return Vec::new(),
            Some(double) => &double.calls,
        };
        let size = calls.len() as i64;
        let n = n as i64;
        if n == 0 || n.abs() > size {
            return Vec::new();
        }
        let index = if n > 0 { n - 1 } else { size + n } as usize;
        let call = &self.log[calls[index]];
        let mut result = vec![call.method.clone()];
        result.extend(call.args.iter().cloned());
        result
    }

    pub fn in_order(&mut self, steps: Vec<Vec<String>>) -> bool {
        let mut step = 0;
        for call in &self.log {
            if step == steps.len() {
                break;
            }
            let wanted = &steps[step];
            if wanted[0] == call.name && wanted[1] == call.method && fits(&wanted[2..], &call.args) {
                step += 1;
            }
        }
        step == steps.len()
    }

    // Level 3
    pub fn add_mock(&mut self, name: String, strict: bool) -> bool {
        self.add(name, true, strict)
    }

    pub fn expect(
        &mut self,
        name: String,
        method: String,
        args: Vec<String>,
        answer: String,
        times: i32,
    ) -> bool {
        match self.doubles.get_mut(&name) {
            Some(double) if double.mock => {
                double.expectations.push(Expectation { method, pattern: args, answer, times, used: 0 });
                true
            }
            _ => false,
        }
    }

    pub fn verify(&mut self, name: String) -> Vec<String> {
        let double = match self.doubles.get(&name) {
            None => return vec![UNKNOWN.to_string()],
            Some(double) => double,
        };
        let mut report: Vec<String> = double
            .expectations
            .iter()
            .filter(|e| e.used < e.times)
            .map(|e| format!("missing {}.{}({}) {}/{}", name, e.method, e.pattern.join(","), e.used, e.times))
            .collect();
        for (method, args) in &double.unexpected {
            report.push(format!("unexpected {}.{}({})", name, method, args.join(",")));
        }
        report
    }

    pub fn verify_all(&mut self) -> Vec<String> {
        let mocks: Vec<String> =
            self.order.iter().filter(|name| self.doubles[*name].mock).cloned().collect();
        mocks.into_iter().flat_map(|name| self.verify(name)).collect()
    }

    // Level 4
    pub fn now(&mut self) -> i64 {
        self.clock
    }

    pub fn schedule(&mut self, delay: i64, name: String, method: String, args: Vec<String>) -> i32 {
        self.timer(delay, 0, name, method, args)
    }

    pub fn every(&mut self, interval: i64, name: String, method: String, args: Vec<String>) -> i32 {
        self.timer(interval, interval, name, method, args)
    }

    pub fn cancel(&mut self, timer_id: i32) -> bool {
        if timer_id < 1 || timer_id as usize > self.timers.len() {
            return false;
        }
        let timer = &mut self.timers[timer_id as usize - 1];
        if timer.stopped {
            return false;
        }
        timer.stopped = true;
        true
    }

    pub fn advance(&mut self, ms: i64) -> Vec<String> {
        let end = self.clock + ms;
        let mut fired = Vec::new();
        while let Some(&Reverse((due, _, timer_id))) = self.heap.peek() {
            if due > end {
                break;
            }
            self.heap.pop();
            let (stopped, interval) = {
                let timer = &self.timers[timer_id - 1];
                (timer.stopped, timer.interval)
            };
            if stopped {
                continue;
            }
            self.clock = due;
            if interval > 0 {
                self.push(due + interval, timer_id);
            } else {
                self.timers[timer_id - 1].stopped = true;
            }
            fired.push(format!("{}@{}", timer_id, due));
            let timer = &self.timers[timer_id - 1];
            let (name, method, args) = (timer.name.clone(), timer.method.clone(), timer.args.clone());
            self.call(name, method, args);
        }
        self.clock = end;
        fired
    }

    pub fn pending(&mut self) -> Vec<String> {
        let mut live: Vec<(i64, i64, usize)> = self
            .heap
            .iter()
            .map(|Reverse(entry)| *entry)
            .filter(|entry| !self.timers[entry.2 - 1].stopped)
            .collect();
        live.sort();
        live.iter().map(|(due, _, timer_id)| format!("{}@{}", timer_id, due)).collect()
    }

    pub fn call_times(&mut self, name: String, method: String) -> Vec<i64> {
        match self.doubles.get(&name) {
            None => Vec::new(),
            Some(double) => double
                .calls
                .iter()
                .map(|&position| &self.log[position])
                .filter(|call| call.method == method)
                .map(|call| call.time)
                .collect(),
        }
    }

    fn count(&self, name: &str, method: &str, pattern: Option<&Vec<String>>) -> i32 {
        match self.doubles.get(name) {
            None => -1,
            Some(double) => double
                .calls
                .iter()
                .map(|&position| &self.log[position])
                .filter(|call| call.method == method && pattern.map_or(true, |p| fits(p, &call.args)))
                .count() as i32,
        }
    }

    fn add(&mut self, name: String, mock: bool, strict: bool) -> bool {
        if self.doubles.contains_key(&name) {
            return false;
        }
        self.order.push(name.clone());
        self.doubles.insert(name, Double::new(mock, strict));
        true
    }

    fn timer(&mut self, delay: i64, interval: i64, name: String, method: String, args: Vec<String>) -> i32 {
        if !self.doubles.contains_key(&name) {
            return -1;
        }
        self.timers.push(Timer { name, method, args, interval, stopped: false });
        let timer_id = self.timers.len();
        self.push(self.clock + delay, timer_id);
        timer_id as i32
    }

    fn push(&mut self, due: i64, timer_id: usize) {
        self.sequence += 1;
        self.heap.push(Reverse((due, self.sequence, timer_id)));
    }
}
