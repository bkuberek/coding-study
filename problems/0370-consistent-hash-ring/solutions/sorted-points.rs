use std::collections::{BTreeMap, HashMap, HashSet};

const RING_SIZE: i64 = 1 << 32;

/// FNV-1a, 32 bits, over the bytes of the text, which Rust strings hold as UTF-8.
fn fnv1a(text: &str) -> i64 {
    let mut value: u32 = 2166136261;
    for byte in text.as_bytes() {
        value = (value ^ u32::from(*byte)).wrapping_mul(16777619);
    }
    i64::from(value)
}

/// Point 0 is the bare name and point i is `i#node`: the number goes first, because FNV-1a mixes
/// the first bytes of a text far better than its last ones.
fn labels_of(node: &str, count: i32) -> Vec<String> {
    let mut labels = vec![node.to_string()];
    labels.extend((1..count).map(|index| format!("{index}#{node}")));
    labels
}

/// A point is `(position, label, node)`; sorting the tuples gives the ring order with its tie-break.
type Point = (i64, String, String);

/// The index of the first point at or after the position, wrapping to 0 past the last one.
fn start_of(ring: &[Point], position: i64) -> usize {
    let index = ring.partition_point(|point| point.0 < position);
    if index == ring.len() {
        0
    } else {
        index
    }
}

fn owner_in(ring: &[Point], position: i64) -> String {
    if ring.is_empty() {
        String::new()
    } else {
        ring[start_of(ring, position)].2.clone()
    }
}

fn modulo_in(order: &[String], key: &str) -> String {
    if order.is_empty() {
        String::new()
    } else {
        order[(fnv1a(key) % order.len() as i64) as usize].clone()
    }
}

/// The ring is a vector of points sorted by position and then by label. A key's owner is the
/// first point at or after the key's position, found by binary search, wrapping to the first point.
pub struct HashRing {
    points: Vec<Point>,
    joined: Vec<String>,
    counts: HashMap<String, i32>,
    tracked: HashSet<String>,
    report: Vec<Vec<String>>,
}

impl HashRing {
    pub fn new() -> Self {
        HashRing {
            points: Vec::new(),
            joined: Vec::new(),
            counts: HashMap::new(),
            tracked: HashSet::new(),
            report: Vec::new(),
        }
    }

    // Level 1
    pub fn position_of(&mut self, text: String) -> i64 {
        fnv1a(&text)
    }

    pub fn add_node(&mut self, node: String) -> i64 {
        if self.add_virtual_node(node.clone(), 1) {
            fnv1a(&node)
        } else {
            -1
        }
    }

    pub fn remove_node(&mut self, node: String) -> bool {
        if !self.counts.contains_key(&node) {
            return false;
        }
        let before = self.owners();
        self.points.retain(|point| point.2 != node);
        self.joined.retain(|name| *name != node);
        self.counts.remove(&node);
        self.make_report(before);
        true
    }

    pub fn nodes(&mut self) -> Vec<String> {
        self.sorted_nodes()
    }

    pub fn node_for(&mut self, key: String) -> String {
        owner_in(&self.points, fnv1a(&key))
    }

    pub fn modulo_node_for(&mut self, key: String) -> String {
        modulo_in(&self.joined, &key)
    }

    pub fn count_moves(&mut self, keys: Vec<String>, node: String) -> Vec<i32> {
        if self.counts.contains_key(&node) {
            return Vec::new();
        }
        let mut grown = self.points.clone();
        grown.push((fnv1a(&node), node.clone(), node.clone()));
        grown.sort();
        let mut order = self.joined.clone();
        order.push(node);
        let mut ring_moves = 0;
        let mut modulo_moves = 0;
        for key in &keys {
            let position = fnv1a(key);
            if owner_in(&self.points, position) != owner_in(&grown, position) {
                ring_moves += 1;
            }
            if modulo_in(&self.joined, key) != modulo_in(&order, key) {
                modulo_moves += 1;
            }
        }
        vec![ring_moves, modulo_moves]
    }

    // Level 2
    pub fn add_virtual_node(&mut self, node: String, count: i32) -> bool {
        if self.counts.contains_key(&node) || count < 1 {
            return false;
        }
        let before = self.owners();
        for label in labels_of(&node, count) {
            self.points.push((fnv1a(&label), label, node.clone()));
        }
        self.points.sort();
        self.joined.push(node.clone());
        self.counts.insert(node, count);
        self.make_report(before);
        true
    }

    pub fn positions(&mut self, node: String) -> Vec<i64> {
        match self.counts.get(&node) {
            Some(&count) => labels_of(&node, count).iter().map(|label| fnv1a(label)).collect(),
            None => Vec::new(),
        }
    }

    pub fn arc_share(&mut self) -> Vec<i64> {
        let mut share: HashMap<&str, i64> = HashMap::new();
        let size = self.points.len();
        for (index, point) in self.points.iter().enumerate() {
            let previous = self.points[(index + size - 1) % size].0;
            let arc = if index > 0 { point.0 - previous } else { point.0 - previous + RING_SIZE };
            *share.entry(point.2.as_str()).or_insert(0) += arc;
        }
        self.sorted_nodes().iter().map(|node| share.get(node.as_str()).copied().unwrap_or(0)).collect()
    }

    pub fn key_counts(&mut self, keys: Vec<String>) -> Vec<i32> {
        let mut owned: HashMap<String, i32> = HashMap::new();
        for key in &keys {
            *owned.entry(owner_in(&self.points, fnv1a(key))).or_insert(0) += 1;
        }
        self.sorted_nodes().iter().map(|node| owned.get(node).copied().unwrap_or(0)).collect()
    }

    // Level 3
    pub fn track_keys(&mut self, keys: Vec<String>) -> i32 {
        self.tracked.extend(keys);
        self.tracked.len() as i32
    }

    pub fn last_moves(&mut self) -> Vec<Vec<String>> {
        self.report.clone()
    }

    pub fn owned_keys(&mut self, node: String) -> Vec<String> {
        if !self.counts.contains_key(&node) {
            return Vec::new();
        }
        let mut owned: Vec<String> = self
            .tracked
            .iter()
            .filter(|key| owner_in(&self.points, fnv1a(key)) == node)
            .cloned()
            .collect();
        owned.sort();
        owned
    }

    // Level 4
    pub fn replicas(&mut self, key: String, count: i32) -> Vec<String> {
        let mut found: Vec<String> = Vec::new();
        if count < 1 || self.points.is_empty() {
            return found;
        }
        let start = start_of(&self.points, fnv1a(&key));
        let size = self.points.len();
        for step in 0..size {
            if found.len() == count as usize {
                break;
            }
            let node = &self.points[(start + step) % size].2;
            if !found.contains(node) {
                found.push(node.clone());
            }
        }
        found
    }

    pub fn assign_bounded(&mut self, keys: Vec<String>, numerator: i32, denominator: i32) -> Vec<String> {
        if self.points.is_empty() || keys.is_empty() {
            return Vec::new();
        }
        let total = i64::from(denominator + numerator) * keys.len() as i64;
        let share = i64::from(denominator) * self.joined.len() as i64;
        let capacity = (total + share - 1) / share;
        let size = self.points.len();
        let mut load: HashMap<&str, i64> = HashMap::new();
        let mut assigned = Vec::with_capacity(keys.len());
        for key in &keys {
            let mut index = start_of(&self.points, fnv1a(key));
            while load.get(self.points[index].2.as_str()).copied().unwrap_or(0) >= capacity {
                index = (index + 1) % size;
            }
            let node = self.points[index].2.as_str();
            *load.entry(node).or_insert(0) += 1;
            assigned.push(node.to_string());
        }
        assigned
    }

    // Shared
    fn sorted_nodes(&self) -> Vec<String> {
        let mut sorted = self.joined.clone();
        sorted.sort();
        sorted
    }

    fn owners(&self) -> BTreeMap<String, String> {
        self.tracked.iter().map(|key| (key.clone(), owner_in(&self.points, fnv1a(key)))).collect()
    }

    /// The owners before a change are kept in a `BTreeMap`, so the rows come out sorted by key.
    fn make_report(&mut self, before: BTreeMap<String, String>) {
        self.report = before
            .into_iter()
            .filter_map(|(key, from)| {
                let to = owner_in(&self.points, fnv1a(&key));
                (to != from).then(|| vec![key, from, to])
            })
            .collect();
    }
}
