use std::collections::HashMap;

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

/// The doubly linked list lives in a `Vec` and links by slot index: safe Rust allows that,
/// where nodes pointing at each other would need `Rc`, `RefCell` and `Weak`.
pub struct LRUCache {
    capacity: usize,
    nodes: Vec<Node>,
    slots: HashMap<i32, usize>,
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
        LRUCache {
            capacity,
            nodes,
            slots: HashMap::with_capacity(capacity),
        }
    }

    pub fn get(&mut self, key: i32) -> i32 {
        let Some(&slot) = self.slots.get(&key) else {
            return -1;
        };
        self.unlink(slot);
        self.append(slot);
        self.nodes[slot].value
    }

    pub fn put(&mut self, key: i32, value: i32) {
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
