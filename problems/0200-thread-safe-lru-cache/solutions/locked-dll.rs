use std::collections::HashMap;
use std::sync::Mutex;

/// The sentinels' slots: `HEAD`'s next is the least recently used node, `TAIL`'s previous the
/// most recent.
const HEAD: usize = 0;
const TAIL: usize = 1;

struct Node {
    key: i32,
    value: i32,
    prev: usize,
    next: usize,
}

/// The sequential cache: a doubly linked list in a `Vec`, linked by slot index, and a map from
/// key to slot.
struct Entries {
    capacity: usize,
    nodes: Vec<Node>,
    slots: HashMap<i32, usize>,
}

/// One mutex guards the map and the list together: every method changes both or must see them
/// consistent, a hit included. The worker threads share the cache, so methods take `&self`
/// and reach the entries through the lock.
pub struct LRUCache {
    entries: Mutex<Entries>,
}

impl LRUCache {
    pub fn new(capacity: i32) -> Self {
        let capacity = capacity as usize;
        let sentinel = || Node {
            key: 0,
            value: 0,
            prev: HEAD,
            next: TAIL,
        };
        let mut nodes = Vec::with_capacity(capacity + 2);
        nodes.extend([sentinel(), sentinel()]);
        let entries = Entries {
            capacity,
            nodes,
            slots: HashMap::with_capacity(capacity),
        };
        LRUCache {
            entries: Mutex::new(entries),
        }
    }

    pub fn get(&self, key: i32) -> i32 {
        self.entries.lock().unwrap().get(key)
    }

    pub fn put(&self, key: i32, value: i32) {
        self.entries.lock().unwrap().put(key, value);
    }

    pub fn size(&self) -> i32 {
        self.entries.lock().unwrap().slots.len() as i32
    }
}

impl Entries {
    fn get(&mut self, key: i32) -> i32 {
        let Some(&slot) = self.slots.get(&key) else {
            return -1;
        };
        self.unlink(slot);
        self.append(slot);
        self.nodes[slot].value
    }

    fn put(&mut self, key: i32, value: i32) {
        if let Some(&slot) = self.slots.get(&key) {
            self.nodes[slot].value = value;
            self.unlink(slot);
            self.append(slot);
            return;
        }
        let slot = if self.slots.len() == self.capacity {
            let oldest = self.nodes[HEAD].next;
            self.unlink(oldest);
            self.slots.remove(&self.nodes[oldest].key);
            self.nodes[oldest].key = key;
            self.nodes[oldest].value = value;
            oldest
        } else {
            self.nodes.push(Node {
                key,
                value,
                prev: HEAD,
                next: TAIL,
            });
            self.nodes.len() - 1
        };
        self.slots.insert(key, slot);
        self.append(slot);
    }

    fn unlink(&mut self, slot: usize) {
        let (prev, next) = (self.nodes[slot].prev, self.nodes[slot].next);
        self.nodes[prev].next = next;
        self.nodes[next].prev = prev;
    }

    fn append(&mut self, slot: usize) {
        let last = self.nodes[TAIL].prev;
        self.nodes[last].next = slot;
        self.nodes[slot].prev = last;
        self.nodes[slot].next = TAIL;
        self.nodes[TAIL].prev = slot;
    }
}
