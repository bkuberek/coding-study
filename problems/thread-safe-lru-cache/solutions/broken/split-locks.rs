use std::collections::HashMap;
use std::sync::Mutex;

const HEAD: usize = 0;
const TAIL: usize = 1;

struct Node {
    key: i32,
    value: i32,
    prev: usize,
    next: usize,
}

struct Order {
    nodes: Vec<Node>,
}

pub struct LRUCache {
    capacity: usize,
    slots: Mutex<HashMap<i32, usize>>,
    order: Mutex<Order>,
}

impl LRUCache {
    pub fn new(capacity: i32) -> Self {
        let sentinel = || Node {
            key: 0,
            value: 0,
            prev: HEAD,
            next: TAIL,
        };
        LRUCache {
            capacity: capacity as usize,
            slots: Mutex::new(HashMap::new()),
            order: Mutex::new(Order {
                nodes: vec![sentinel(), sentinel()],
            }),
        }
    }

    pub fn get(&self, key: i32) -> i32 {
        let Some(slot) = self.slots.lock().unwrap().get(&key).copied() else {
            return -1;
        };
        let mut order = self.order.lock().unwrap();
        order.unlink(slot);
        order.append(slot);
        order.nodes[slot].value
    }

    pub fn put(&self, key: i32, value: i32) {
        let existing = self.slots.lock().unwrap().get(&key).copied();
        if let Some(slot) = existing {
            let mut order = self.order.lock().unwrap();
            order.nodes[slot].value = value;
            order.unlink(slot);
            order.append(slot);
            return;
        }
        let mut order = self.order.lock().unwrap();
        let mut slots = self.slots.lock().unwrap();
        let slot = if slots.len() == self.capacity {
            let oldest = order.nodes[HEAD].next;
            order.unlink(oldest);
            slots.remove(&order.nodes[oldest].key);
            order.nodes[oldest].key = key;
            order.nodes[oldest].value = value;
            oldest
        } else {
            order.nodes.push(Node {
                key,
                value,
                prev: HEAD,
                next: TAIL,
            });
            order.nodes.len() - 1
        };
        slots.insert(key, slot);
        order.append(slot);
    }

    pub fn size(&self) -> i32 {
        self.slots.lock().unwrap().len() as i32
    }
}

impl Order {
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
