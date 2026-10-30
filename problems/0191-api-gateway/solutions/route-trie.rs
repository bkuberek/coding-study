use std::collections::{HashMap, VecDeque};

const NOT_FOUND: &str = "404";
const TOO_MANY_REQUESTS: &str = "429";
const UNAVAILABLE: &str = "503";

fn segments(path: &str) -> Vec<&str> {
    path.split('/')
        .filter(|segment| !segment.is_empty())
        .collect()
}

/// One trie level: literal children, one shared parameter child, and the routes ending here.
#[derive(Default)]
struct RouteNode {
    literals: HashMap<String, RouteNode>,
    parameter: Option<Box<RouteNode>>,
    /// A pattern ending exactly here.
    upstream: Option<String>,
    /// A pattern ending here with `*`.
    wildcard: Option<String>,
}

impl RouteNode {
    fn child(&mut self, segment: &str) -> &mut RouteNode {
        if segment.starts_with(':') {
            return self.parameter.get_or_insert_with(Box::default);
        }
        self.literals.entry(segment.to_string()).or_default()
    }

    fn slot(&mut self, wildcard: bool) -> &mut Option<String> {
        if wildcard {
            &mut self.wildcard
        } else {
            &mut self.upstream
        }
    }

    /// The most specific upstream: literal before parameter before wildcard, left to right.
    fn find(&self, path: &[&str], index: usize) -> Option<&str> {
        if index == path.len() {
            return self.upstream.as_deref();
        }
        let mut found = self
            .literals
            .get(path[index])
            .and_then(|literal| literal.find(path, index + 1));
        if found.is_none() {
            if let Some(parameter) = &self.parameter {
                found = parameter.find(path, index + 1);
            }
        }
        found.or(self.wildcard.as_deref())
    }
}

#[derive(Default)]
struct RouteTable {
    roots: HashMap<String, RouteNode>,
}

impl RouteTable {
    fn add(&mut self, method: &str, pattern: &str, upstream: &str) -> bool {
        let (node, wildcard) = self.end(method, pattern);
        let slot = node.slot(wildcard);
        if slot.is_some() {
            return false;
        }
        *slot = Some(upstream.to_string());
        true
    }

    fn remove(&mut self, method: &str, pattern: &str) -> bool {
        let (node, wildcard) = self.end(method, pattern);
        node.slot(wildcard).take().is_some()
    }

    fn find(&self, method: &str, path: &str) -> Option<&str> {
        self.roots.get(method)?.find(&segments(path), 0)
    }

    /// The node where `pattern` ends, and whether it ends with the wildcard.
    fn end(&mut self, method: &str, pattern: &str) -> (&mut RouteNode, bool) {
        let mut parts = segments(pattern);
        let wildcard = parts.last() == Some(&"*");
        if wildcard {
            parts.pop();
        }
        let mut node = self.roots.entry(method.to_string()).or_default();
        for part in parts {
            node = node.child(part);
        }
        (node, wildcard)
    }
}

struct FixedWindow {
    limit: i32,
    window: i64,
    current: i64,
    used: i32,
}

impl FixedWindow {
    fn allows(&self, now: i64) -> bool {
        now / self.window != self.current || self.used < self.limit
    }

    fn record(&mut self, now: i64) {
        if now / self.window != self.current {
            self.current = now / self.window;
            self.used = 0;
        }
        self.used += 1;
    }
}

struct SlidingWindow {
    limit: usize,
    window: i64,
    accepted: VecDeque<i64>,
}

impl SlidingWindow {
    fn allows(&mut self, now: i64) -> bool {
        while self
            .accepted
            .front()
            .is_some_and(|&accepted| accepted <= now - self.window)
        {
            self.accepted.pop_front();
        }
        self.accepted.len() < self.limit
    }

    fn record(&mut self, now: i64) {
        self.accepted.push_back(now);
    }
}

enum Limiter {
    Fixed(FixedWindow),
    Sliding(SlidingWindow),
}

#[derive(Default)]
struct Client {
    limiter: Option<Limiter>,
    /// Requests left, when a quota is set.
    quota: Option<i64>,
}

impl Client {
    fn allows(&mut self, now: i64) -> bool {
        let within_rate = match &mut self.limiter {
            None => true,
            Some(Limiter::Fixed(window)) => window.allows(now),
            Some(Limiter::Sliding(window)) => window.allows(now),
        };
        within_rate && self.quota.map_or(true, |quota| quota > 0)
    }

    fn record(&mut self, now: i64) {
        match &mut self.limiter {
            None => {}
            Some(Limiter::Fixed(window)) => window.record(now),
            Some(Limiter::Sliding(window)) => window.record(now),
        }
        if let Some(quota) = &mut self.quota {
            *quota -= 1;
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum State {
    Closed,
    Open,
    HalfOpen,
}

impl State {
    fn name(self) -> &'static str {
        match self {
            State::Closed => "CLOSED",
            State::Open => "OPEN",
            State::HalfOpen => "HALF_OPEN",
        }
    }
}

struct CircuitBreaker {
    threshold: i32,
    cooldown: i64,
    failures: i32,
    opened_at: Option<i64>,
    trial_in_flight: bool,
}

impl CircuitBreaker {
    fn state(&self, now: i64) -> State {
        match self.opened_at {
            None => State::Closed,
            Some(opened_at) if now >= opened_at + self.cooldown => State::HalfOpen,
            Some(_) => State::Open,
        }
    }

    fn allows(&self, now: i64) -> bool {
        match self.state(now) {
            State::Closed => true,
            State::HalfOpen => !self.trial_in_flight,
            State::Open => false,
        }
    }

    fn on_dispatch(&mut self, now: i64) {
        if self.state(now) == State::HalfOpen {
            self.trial_in_flight = true;
        }
    }

    fn record(&mut self, now: i64, success: bool) -> State {
        match self.state(now) {
            State::HalfOpen => {
                self.trial_in_flight = false;
                self.opened_at = if success { None } else { Some(now) };
            }
            State::Closed => {
                self.failures = if success { 0 } else { self.failures + 1 };
                if self.failures >= self.threshold {
                    self.failures = 0;
                    self.opened_at = Some(now);
                }
            }
            State::Open => {}
        }
        self.state(now)
    }
}

pub struct ApiGateway {
    routes: RouteTable,
    clients: HashMap<String, Client>,
    breakers: HashMap<String, CircuitBreaker>,
}

impl ApiGateway {
    pub fn new() -> Self {
        ApiGateway {
            routes: RouteTable::default(),
            clients: HashMap::new(),
            breakers: HashMap::new(),
        }
    }

    // Level 1
    pub fn add_route(
        &mut self,
        timestamp: i64,
        method: String,
        pattern: String,
        upstream: String,
    ) -> bool {
        self.routes.add(&method, &pattern, &upstream)
    }

    // Level 1
    pub fn remove_route(&mut self, timestamp: i64, method: String, pattern: String) -> bool {
        self.routes.remove(&method, &pattern)
    }

    // Level 1
    pub fn route(
        &mut self,
        timestamp: i64,
        client_id: String,
        method: String,
        path: String,
    ) -> String {
        let Some(upstream) = self.routes.find(&method, &path).map(str::to_string) else {
            return NOT_FOUND.to_string();
        };
        if let Some(breaker) = self.breakers.get(&upstream) {
            if !breaker.allows(timestamp) {
                return UNAVAILABLE.to_string();
            }
        }
        if let Some(client) = self.clients.get_mut(&client_id) {
            if !client.allows(timestamp) {
                return TOO_MANY_REQUESTS.to_string();
            }
            client.record(timestamp);
        }
        if let Some(breaker) = self.breakers.get_mut(&upstream) {
            breaker.on_dispatch(timestamp);
        }
        upstream
    }

    // Level 2
    pub fn set_client_limit(
        &mut self,
        timestamp: i64,
        client_id: String,
        limit: i32,
        window_ms: i64,
    ) {
        self.client(client_id).limiter = Some(Limiter::Fixed(FixedWindow {
            limit,
            window: window_ms,
            current: -1,
            used: 0,
        }));
    }

    // Level 3
    pub fn set_client_sliding_limit(
        &mut self,
        timestamp: i64,
        client_id: String,
        limit: i32,
        window_ms: i64,
    ) {
        self.client(client_id).limiter = Some(Limiter::Sliding(SlidingWindow {
            limit: limit as usize,
            window: window_ms,
            accepted: VecDeque::new(),
        }));
    }

    // Level 3
    pub fn set_client_quota(&mut self, timestamp: i64, client_id: String, quota: i64) {
        self.client(client_id).quota = Some(quota);
    }

    // Level 3
    pub fn remaining_quota(&mut self, timestamp: i64, client_id: String) -> i64 {
        self.clients
            .get(&client_id)
            .and_then(|client| client.quota)
            .unwrap_or(-1)
    }

    // Level 4
    pub fn set_breaker(
        &mut self,
        timestamp: i64,
        upstream: String,
        failure_threshold: i32,
        cooldown_ms: i64,
    ) {
        self.breakers.insert(
            upstream,
            CircuitBreaker {
                threshold: failure_threshold,
                cooldown: cooldown_ms,
                failures: 0,
                opened_at: None,
                trial_in_flight: false,
            },
        );
    }

    // Level 4
    pub fn report_result(&mut self, timestamp: i64, upstream: String, success: bool) -> String {
        match self.breakers.get_mut(&upstream) {
            Some(breaker) => breaker.record(timestamp, success).name().to_string(),
            None => String::new(),
        }
    }

    // Level 4
    pub fn breaker_state(&mut self, timestamp: i64, upstream: String) -> String {
        match self.breakers.get(&upstream) {
            Some(breaker) => breaker.state(timestamp).name().to_string(),
            None => String::new(),
        }
    }

    fn client(&mut self, client_id: String) -> &mut Client {
        self.clients.entry(client_id).or_default()
    }
}
