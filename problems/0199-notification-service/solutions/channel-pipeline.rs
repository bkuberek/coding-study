use std::cmp::{Ordering, Reverse};
use std::collections::{BinaryHeap, HashMap, VecDeque};

const CHANNEL_ORDER: [&str; 3] = ["EMAIL", "SMS", "PUSH"];
const MAX_RETRIES: u32 = 3;
const BASE_RETRY_DELAY: i64 = 1000;

trait Channel {
    fn format(&self, address: &str, text: &str) -> String;
}

struct EmailChannel;

impl Channel for EmailChannel {
    fn format(&self, address: &str, text: &str) -> String {
        format!("{address}: {text}")
    }
}

/// A channel with a length limit: a longer text is cut so that it ends in `...` and fits.
struct TruncatingChannel {
    limit: usize,
}

impl Channel for TruncatingChannel {
    fn format(&self, address: &str, text: &str) -> String {
        if text.chars().count() > self.limit {
            let kept: String = text.chars().take(self.limit - 3).collect();
            return format!("{address}: {kept}...");
        }
        format!("{address}: {text}")
    }
}

struct Template {
    body: String,
}

impl Template {
    /// Replaces every `{name}` (a brace-free name between braces) with the value of the
    /// `name=value` parameter, or with nothing when there is none.
    fn render(&self, params: &[String]) -> String {
        let values: HashMap<&str, &str> = params
            .iter()
            .filter_map(|param| param.split_once('='))
            .collect();
        let mut text = String::new();
        let mut rest = self.body.as_str();
        while let Some(open) = rest.find('{') {
            text.push_str(&rest[..open]);
            let inside = &rest[open + 1..];
            // A placeholder runs to the first brace after its name, which must be a `}`.
            match inside.find(['{', '}']) {
                Some(close) if inside[close..].starts_with('}') => {
                    text.push_str(values.get(&inside[..close]).copied().unwrap_or(""));
                    rest = &inside[close + 1..];
                }
                _ => {
                    text.push('{');
                    rest = inside;
                }
            }
        }
        text.push_str(rest);
        text
    }
}

/// At most `limit` accepted notifications per user in any `window` milliseconds.
struct SlidingWindowLimiter {
    limit: usize,
    window: i64,
    accepted: HashMap<String, VecDeque<i64>>,
}

impl SlidingWindowLimiter {
    fn try_acquire(&mut self, user_id: &str, now: i64) -> bool {
        let times = self.accepted.entry(user_id.to_string()).or_default();
        while times.front().is_some_and(|&time| time <= now - self.window) {
            times.pop_front();
        }
        if times.len() >= self.limit {
            return false;
        }
        times.push_back(now);
        true
    }
}

struct ChannelState {
    channel: Box<dyn Channel>,
    limiter: Option<SlidingWindowLimiter>,
    outage: Option<(i64, i64)>,
    delivered: i32,
    retries: i32,
    dropped: i32,
    rate_limited: i32,
}

impl ChannelState {
    fn new(channel: Box<dyn Channel>) -> Self {
        ChannelState {
            channel,
            limiter: None,
            outage: None,
            delivered: 0,
            retries: 0,
            dropped: 0,
            rate_limited: 0,
        }
    }

    fn is_down(&self, now: i64) -> bool {
        self.outage
            .is_some_and(|(start, end)| start <= now && now < end)
    }

    fn stats(&self) -> Vec<i32> {
        vec![
            self.delivered,
            self.retries,
            self.dropped,
            self.rate_limited,
        ]
    }
}

struct Contact {
    address: String,
    enabled: bool,
}

/// One delivery attempt. Attempts order by `(due, sequence)` only, so the retry heap pops the
/// earliest one first and equal due times in the order they were scheduled.
struct Attempt {
    due: i64,
    sequence: u64,
    user_id: String,
    channel: String,
    payload: String,
    retries_left: u32,
}

impl PartialEq for Attempt {
    fn eq(&self, other: &Self) -> bool {
        self.cmp(other) == Ordering::Equal
    }
}

impl Eq for Attempt {}

impl PartialOrd for Attempt {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for Attempt {
    fn cmp(&self, other: &Self) -> Ordering {
        (self.due, self.sequence).cmp(&(other.due, other.sequence))
    }
}

pub struct NotificationService {
    channels: HashMap<String, ChannelState>,
    contacts: HashMap<(String, String), Contact>,
    templates: HashMap<String, Template>,
    /// Min-heap by `(due, sequence)`.
    retries: BinaryHeap<Reverse<Attempt>>,
    sequence: u64,
    inbox: HashMap<(String, String), Vec<String>>,
}

impl NotificationService {
    pub fn new() -> Self {
        let channels = HashMap::from([
            (
                "EMAIL".to_string(),
                ChannelState::new(Box::new(EmailChannel)),
            ),
            (
                "SMS".to_string(),
                ChannelState::new(Box::new(TruncatingChannel { limit: 20 })),
            ),
            (
                "PUSH".to_string(),
                ChannelState::new(Box::new(TruncatingChannel { limit: 30 })),
            ),
        ]);
        NotificationService {
            channels,
            contacts: HashMap::new(),
            templates: HashMap::new(),
            retries: BinaryHeap::new(),
            sequence: 0,
            inbox: HashMap::new(),
        }
    }

    pub fn add_contact(&mut self, user_id: String, channel: String, address: String) -> bool {
        if !self.channels.contains_key(&channel) {
            return false;
        }
        let contact = Contact {
            address,
            enabled: true,
        };
        self.contacts.insert((user_id, channel), contact);
        true
    }

    pub fn set_preference(&mut self, user_id: String, channel: String, enabled: bool) -> bool {
        match self.contacts.get_mut(&(user_id, channel)) {
            Some(contact) => {
                contact.enabled = enabled;
                true
            }
            None => false,
        }
    }

    pub fn add_template(&mut self, template_id: String, body: String) -> bool {
        if self.templates.contains_key(&template_id) {
            return false;
        }
        self.templates.insert(template_id, Template { body });
        true
    }

    pub fn set_rate_limit(&mut self, channel: String, limit: i32, window_ms: i64) -> bool {
        match self.channels.get_mut(&channel) {
            Some(state) => {
                state.limiter = Some(SlidingWindowLimiter {
                    limit: usize::try_from(limit).unwrap_or(0),
                    window: window_ms,
                    accepted: HashMap::new(),
                });
                true
            }
            None => false,
        }
    }

    pub fn set_outage(&mut self, channel: String, start: i64, end: i64) -> bool {
        match self.channels.get_mut(&channel) {
            Some(state) => {
                state.outage = Some((start, end));
                true
            }
            None => false,
        }
    }

    pub fn send(
        &mut self,
        timestamp: i64,
        user_id: String,
        template_id: String,
        params: Vec<String>,
    ) -> i32 {
        self.process_retries(timestamp);
        let Some(template) = self.templates.get(&template_id) else {
            return -1;
        };
        let text = template.render(&params);
        let mut accepted = 0;
        for name in CHANNEL_ORDER {
            let key = (user_id.clone(), name.to_string());
            let Some(contact) = self.contacts.get(&key).filter(|contact| contact.enabled) else {
                continue;
            };
            let Some(state) = self.channels.get_mut(name) else {
                continue;
            };
            if let Some(limiter) = &mut state.limiter {
                if !limiter.try_acquire(&user_id, timestamp) {
                    state.rate_limited += 1;
                    continue;
                }
            }
            accepted += 1;
            let payload = state.channel.format(&contact.address, &text);
            let attempt = self.new_attempt(timestamp, user_id.clone(), name, payload, MAX_RETRIES);
            self.run(attempt);
        }
        accepted
    }

    pub fn delivered(&mut self, timestamp: i64, user_id: String, channel: String) -> Vec<String> {
        self.process_retries(timestamp);
        self.inbox
            .get(&(user_id, channel))
            .cloned()
            .unwrap_or_default()
    }

    pub fn stats(&mut self, timestamp: i64, channel: String) -> Vec<i32> {
        self.process_retries(timestamp);
        self.channels
            .get(&channel)
            .map_or_else(Vec::new, ChannelState::stats)
    }

    fn new_attempt(
        &mut self,
        due: i64,
        user_id: String,
        channel: &str,
        payload: String,
        retries_left: u32,
    ) -> Attempt {
        self.sequence += 1;
        Attempt {
            due,
            sequence: self.sequence,
            user_id,
            channel: channel.to_string(),
            payload,
            retries_left,
        }
    }

    /// Delivers now, or schedules the next retry with an exponentially growing delay.
    fn run(&mut self, attempt: Attempt) {
        let Some(state) = self.channels.get_mut(&attempt.channel) else {
            return;
        };
        if !state.is_down(attempt.due) {
            state.delivered += 1;
            self.inbox
                .entry((attempt.user_id, attempt.channel))
                .or_default()
                .push(attempt.payload);
        } else if attempt.retries_left == 0 {
            state.dropped += 1;
        } else {
            let retry_number = MAX_RETRIES - attempt.retries_left + 1;
            let due = attempt.due + (BASE_RETRY_DELAY << (retry_number - 1));
            let retry = self.new_attempt(
                due,
                attempt.user_id,
                &attempt.channel,
                attempt.payload,
                attempt.retries_left - 1,
            );
            self.retries.push(Reverse(retry));
        }
    }

    fn process_retries(&mut self, now: i64) {
        while self
            .retries
            .peek()
            .is_some_and(|Reverse(attempt)| attempt.due <= now)
        {
            let Some(Reverse(attempt)) = self.retries.pop() else {
                break;
            };
            if let Some(state) = self.channels.get_mut(&attempt.channel) {
                state.retries += 1;
            }
            self.run(attempt);
        }
    }
}
