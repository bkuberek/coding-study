use std::collections::{HashMap, VecDeque};

const NO_SUBSCRIBER: &str = "-";

/// Dot-separated segments; `*` matches exactly one segment and `#` zero or more.
struct TopicPattern {
    segments: Vec<String>,
}

impl TopicPattern {
    fn parse(text: &str) -> Self {
        TopicPattern {
            segments: text.split('.').map(str::to_string).collect(),
        }
    }

    fn matches(&self, topic: &str) -> bool {
        let words: Vec<&str> = topic.split('.').collect();
        let mut memo = vec![None; (self.segments.len() + 1) * (words.len() + 1)];
        self.matches_from(&words, 0, 0, &mut memo)
    }

    /// Whether `segments[p..]` matches `words[w..]`; `memo` caches each `(p, w)` answer.
    fn matches_from(&self, words: &[&str], p: usize, w: usize, memo: &mut [Option<bool>]) -> bool {
        let slot = p * (words.len() + 1) + w;
        if let Some(known) = memo[slot] {
            return known;
        }
        let result = if p == self.segments.len() {
            w == words.len()
        } else if self.segments[p] == "#" {
            self.matches_from(words, p + 1, w, memo)
                || (w < words.len() && self.matches_from(words, p, w + 1, memo))
        } else if w == words.len() {
            false
        } else {
            (self.segments[p] == "*" || self.segments[p] == words[w])
                && self.matches_from(words, p + 1, w + 1, memo)
        };
        memo[slot] = Some(result);
        result
    }
}

#[derive(Clone)]
struct Event {
    topic: String,
    payload: String,
}

impl Event {
    fn render(&self) -> String {
        format!("{}:{}", self.topic, self.payload)
    }
}

struct Subscriber {
    id: String,
    patterns: HashMap<String, TopicPattern>,
    inbox: VecDeque<Event>,
    limit: Option<usize>,
}

impl Subscriber {
    fn new(id: &str) -> Self {
        Subscriber {
            id: id.to_string(),
            patterns: HashMap::new(),
            inbox: VecDeque::new(),
            limit: None,
        }
    }

    fn wants(&self, topic: &str) -> bool {
        self.patterns.values().any(|pattern| pattern.matches(topic))
    }

    /// Accepts the event unless the inbox is full.
    fn offer(&mut self, event: Event) -> bool {
        if self.limit.is_some_and(|limit| self.inbox.len() >= limit) {
            return false;
        }
        self.inbox.push_back(event);
        true
    }

    fn take(&mut self, count: usize) -> Vec<String> {
        let count = count.min(self.inbox.len());
        self.inbox
            .drain(..count)
            .map(|event| event.render())
            .collect()
    }
}

#[derive(Default)]
struct DeadLetterQueue {
    letters: VecDeque<String>,
}

impl DeadLetterQueue {
    fn add(&mut self, subscriber_id: &str, event: &Event) {
        self.letters
            .push_back(format!("{subscriber_id}:{}", event.render()));
    }

    fn drain(&mut self, count: usize) -> Vec<String> {
        let count = count.min(self.letters.len());
        self.letters.drain(..count).collect()
    }
}

pub struct EventBus {
    subscribers: HashMap<String, Subscriber>,
    dead_letters: DeadLetterQueue,
}

impl EventBus {
    pub fn new() -> Self {
        EventBus {
            subscribers: HashMap::new(),
            dead_letters: DeadLetterQueue::default(),
        }
    }

    pub fn subscribe(&mut self, subscriber_id: String, pattern: String) -> bool {
        let subscriber = self
            .subscribers
            .entry(subscriber_id)
            .or_insert_with_key(|id| Subscriber::new(id));
        if subscriber.patterns.contains_key(&pattern) {
            return false;
        }
        let parsed = TopicPattern::parse(&pattern);
        subscriber.patterns.insert(pattern, parsed);
        true
    }

    pub fn unsubscribe(&mut self, subscriber_id: String, pattern: String) -> bool {
        self.subscribers
            .get_mut(&subscriber_id)
            .is_some_and(|subscriber| subscriber.patterns.remove(&pattern).is_some())
    }

    pub fn publish(&mut self, topic: String, payload: String) -> i32 {
        let event = Event {
            topic: topic.clone(),
            payload,
        };
        let mut interested: Vec<&mut Subscriber> = self
            .subscribers
            .values_mut()
            .filter(|subscriber| subscriber.wants(&topic))
            .collect();
        interested.sort_by(|a, b| a.id.cmp(&b.id));
        if interested.is_empty() {
            self.dead_letters.add(NO_SUBSCRIBER, &event);
        }
        let mut delivered = 0;
        for subscriber in interested {
            if subscriber.offer(event.clone()) {
                delivered += 1;
            } else {
                self.dead_letters.add(&subscriber.id, &event);
            }
        }
        delivered
    }

    pub fn poll(&mut self, subscriber_id: String, max_events: i32) -> Vec<String> {
        let count = usize::try_from(max_events).unwrap_or(0);
        match self.subscribers.get_mut(&subscriber_id) {
            Some(subscriber) => subscriber.take(count),
            None => Vec::new(),
        }
    }

    pub fn pending(&mut self, subscriber_id: String) -> i32 {
        self.subscribers
            .get(&subscriber_id)
            .map_or(-1, |subscriber| subscriber.inbox.len() as i32)
    }

    pub fn set_inbox_limit(&mut self, subscriber_id: String, limit: i32) -> bool {
        match self.subscribers.get_mut(&subscriber_id) {
            Some(subscriber) => {
                subscriber.limit = Some(usize::try_from(limit).unwrap_or(0));
                true
            }
            None => false,
        }
    }

    pub fn dead_letters(&mut self, max_events: i32) -> Vec<String> {
        self.dead_letters
            .drain(usize::try_from(max_events).unwrap_or(0))
    }
}
