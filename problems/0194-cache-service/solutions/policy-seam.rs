use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap};

const FIRST: usize = 0;
const END: usize = 1;

struct Link {
    key: String,
    previous: usize,
    next: usize,
}

/// An insertion-ordered set of keys with O(1) move-to-back and removal. The standard library has
/// no ordered map, so the links live in a `Vec` and point at each other by slot index, with
/// sentinels in slots `FIRST` and `END`; a map finds a key's slot.
struct OrderedKeys {
    links: Vec<Link>,
    slots: HashMap<String, usize>,
    spare: Vec<usize>,
}

impl OrderedKeys {
    fn new() -> Self {
        let sentinel = || Link {
            key: String::new(),
            previous: FIRST,
            next: END,
        };
        OrderedKeys {
            links: vec![sentinel(), sentinel()],
            slots: HashMap::new(),
            spare: Vec::new(),
        }
    }

    fn push_back(&mut self, key: &str) {
        let slot = match self.spare.pop() {
            Some(slot) => {
                self.links[slot].key = key.to_string();
                slot
            }
            None => {
                self.links.push(Link {
                    key: key.to_string(),
                    previous: FIRST,
                    next: END,
                });
                self.links.len() - 1
            }
        };
        self.slots.insert(key.to_string(), slot);
        self.append(slot);
    }

    fn move_to_back(&mut self, key: &str) {
        if let Some(&slot) = self.slots.get(key) {
            self.unlink(slot);
            self.append(slot);
        }
    }

    fn remove(&mut self, key: &str) {
        if let Some(slot) = self.slots.remove(key) {
            self.unlink(slot);
            self.spare.push(slot);
        }
    }

    /// The oldest key, if any.
    fn front(&self) -> Option<&str> {
        let first = self.links[FIRST].next;
        (first != END).then(|| self.links[first].key.as_str())
    }

    fn unlink(&mut self, slot: usize) {
        let (previous, next) = (self.links[slot].previous, self.links[slot].next);
        self.links[previous].next = next;
        self.links[next].previous = previous;
    }

    fn append(&mut self, slot: usize) {
        let last = self.links[END].previous;
        self.links[last].next = slot;
        self.links[slot].previous = last;
        self.links[slot].next = END;
        self.links[END].previous = slot;
    }
}

/// Tracks the live keys and names the one to evict when the cache is full.
trait EvictionPolicy {
    fn admit(&mut self, key: &str);
    fn touch(&mut self, key: &str);
    fn forget(&mut self, key: &str);
    fn victim(&mut self) -> String;
}

struct LruPolicy {
    /// Least recently used first.
    order: OrderedKeys,
}

impl LruPolicy {
    fn new() -> Self {
        LruPolicy {
            order: OrderedKeys::new(),
        }
    }
}

impl EvictionPolicy for LruPolicy {
    fn admit(&mut self, key: &str) {
        self.order.push_back(key);
    }

    fn touch(&mut self, key: &str) {
        self.order.move_to_back(key);
    }

    fn forget(&mut self, key: &str) {
        self.order.remove(key);
    }

    fn victim(&mut self) -> String {
        self.order.front().unwrap_or_default().to_string()
    }
}

/// The LRU order without the move: using a key does not change its place, so the oldest
/// insertion goes first.
struct FifoPolicy {
    order: LruPolicy,
}

impl EvictionPolicy for FifoPolicy {
    fn admit(&mut self, key: &str) {
        self.order.admit(key);
    }

    fn touch(&mut self, _key: &str) {}

    fn forget(&mut self, key: &str) {
        self.order.forget(key);
    }

    fn victim(&mut self) -> String {
        self.order.victim()
    }
}

/// Least frequently used first; among equal counts, least recently used first.
struct LfuPolicy {
    counts: HashMap<String, usize>,
    buckets: HashMap<usize, OrderedKeys>,
    /// Never above the lowest count in use.
    lowest: usize,
}

impl LfuPolicy {
    fn new() -> Self {
        LfuPolicy {
            counts: HashMap::new(),
            buckets: HashMap::new(),
            lowest: 1,
        }
    }

    fn place(&mut self, key: &str, count: usize) {
        self.counts.insert(key.to_string(), count);
        self.buckets
            .entry(count)
            .or_insert_with(OrderedKeys::new)
            .push_back(key);
    }

    fn unplace(&mut self, key: &str, count: usize) {
        if let Some(bucket) = self.buckets.get_mut(&count) {
            bucket.remove(key);
        }
    }
}

impl EvictionPolicy for LfuPolicy {
    fn admit(&mut self, key: &str) {
        self.place(key, 1);
        self.lowest = 1;
    }

    fn touch(&mut self, key: &str) {
        let count = self.counts[key];
        self.unplace(key, count);
        self.place(key, count + 1);
    }

    fn forget(&mut self, key: &str) {
        if let Some(count) = self.counts.remove(key) {
            self.unplace(key, count);
        }
    }

    fn victim(&mut self) -> String {
        loop {
            let oldest = self.buckets.get(&self.lowest).and_then(OrderedKeys::front);
            if let Some(key) = oldest {
                return key.to_string();
            }
            self.lowest += 1;
        }
    }
}

fn new_policy(name: &str) -> Box<dyn EvictionPolicy> {
    match name {
        "LRU" => Box::new(LruPolicy::new()),
        "LFU" => Box::new(LfuPolicy::new()),
        "FIFO" => Box::new(FifoPolicy {
            order: LruPolicy::new(),
        }),
        _ => panic!("unknown eviction policy {name}"),
    }
}

struct Entry {
    value: String,
    expires_at: Option<i64>,
}

impl Entry {
    fn expired(&self, now: i64) -> bool {
        self.expires_at.is_some_and(|expires_at| now >= expires_at)
    }
}

pub struct CacheService {
    capacity: usize,
    policy: Box<dyn EvictionPolicy>,
    entries: HashMap<String, Entry>,
    /// Min-heap of `(expires_at, key)`; stale pairs are skipped when they surface.
    expiries: BinaryHeap<Reverse<(i64, String)>>,
    hits: i32,
    misses: i32,
    evictions: i32,
    expirations: i32,
}

impl CacheService {
    pub fn new(capacity: i32, policy: String) -> Self {
        CacheService {
            capacity: capacity as usize,
            policy: new_policy(&policy),
            entries: HashMap::new(),
            expiries: BinaryHeap::new(),
            hits: 0,
            misses: 0,
            evictions: 0,
            expirations: 0,
        }
    }

    pub fn put(&mut self, timestamp: i64, key: String, value: String, ttl: i64) {
        let expires_at = if ttl > 0 { Some(timestamp + ttl) } else { None };
        if self.is_live(timestamp, &key) {
            self.entries
                .insert(key.clone(), Entry { value, expires_at });
            self.policy.touch(&key);
        } else {
            self.make_room(timestamp);
            self.entries
                .insert(key.clone(), Entry { value, expires_at });
            self.policy.admit(&key);
        }
        if let Some(expires_at) = expires_at {
            self.expiries.push(Reverse((expires_at, key)));
        }
    }

    pub fn get(&mut self, timestamp: i64, key: String) -> String {
        if !self.is_live(timestamp, &key) {
            self.misses += 1;
            return String::new();
        }
        self.hits += 1;
        self.policy.touch(&key);
        self.entries[&key].value.clone()
    }

    pub fn remove(&mut self, timestamp: i64, key: String) -> bool {
        if !self.is_live(timestamp, &key) {
            return false;
        }
        self.drop_entry(&key);
        true
    }

    pub fn size(&mut self, timestamp: i64) -> i32 {
        self.purge_expired(timestamp);
        self.entries.len() as i32
    }

    pub fn stats(&mut self) -> Vec<i32> {
        vec![self.hits, self.misses, self.evictions, self.expirations]
    }

    /// Whether `key` holds a live entry; an entry whose time is up is expired on the spot.
    fn is_live(&mut self, now: i64, key: &str) -> bool {
        match self.entries.get(key) {
            Some(entry) if entry.expired(now) => {
                self.expire(key);
                false
            }
            Some(_) => true,
            None => false,
        }
    }

    fn make_room(&mut self, now: i64) {
        if self.entries.len() < self.capacity {
            return;
        }
        self.purge_expired(now);
        if self.entries.len() >= self.capacity {
            let victim = self.policy.victim();
            self.drop_entry(&victim);
            self.evictions += 1;
        }
    }

    fn purge_expired(&mut self, now: i64) {
        while self
            .expiries
            .peek()
            .is_some_and(|Reverse((expires_at, _))| *expires_at <= now)
        {
            let Some(Reverse((expires_at, key))) = self.expiries.pop() else {
                break;
            };
            let current = self
                .entries
                .get(&key)
                .is_some_and(|entry| entry.expires_at == Some(expires_at));
            if current {
                self.expire(&key);
            }
        }
    }

    fn expire(&mut self, key: &str) {
        self.drop_entry(key);
        self.expirations += 1;
    }

    fn drop_entry(&mut self, key: &str) {
        self.entries.remove(key);
        self.policy.forget(key);
    }
}
