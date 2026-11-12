use std::collections::HashMap;

/// One replica's slot of a counter: what it added and what it took away, each with the change
/// number at which it last grew.
#[derive(Default)]
struct Slot {
    up: i64,
    up_at: i64,
    down: i64,
    down_at: i64,
}

#[derive(Clone)]
struct Register {
    text: String,
    timestamp: i64,
    writer: String,
    at: i64,
}

impl Register {
    fn loses_to(&self, timestamp: i64, writer: &str) -> bool {
        (timestamp, writer) > (self.timestamp, self.writer.as_str())
    }
}

struct Tag {
    added_at: i64,
    removed: bool,
    removed_at: i64,
}

impl Tag {
    fn new(added_at: i64) -> Self {
        Tag { added_at, removed: false, removed_at: 0 }
    }
}

type Tags = HashMap<String, Tag>;

/// The whole state of one replica. Every entry (a counter slot's up or down part, a register, an
/// add tag, a tombstone) only grows, and each one remembers the change number at which it last
/// grew, so a sync can pick the entries that changed after the last acknowledgement.
#[derive(Default)]
struct Replica {
    clock: i64,
    adds: i32,
    counters: HashMap<String, HashMap<String, Slot>>,
    registers: HashMap<String, Register>,
    sets: HashMap<String, HashMap<String, Tags>>,
    acked: HashMap<String, i64>,
}

impl Replica {
    fn tick(&mut self) -> i64 {
        self.clock += 1;
        self.clock
    }

    fn slot(&mut self, counter: &str, owner: &str) -> &mut Slot {
        self.counters
            .entry(counter.to_string())
            .or_default()
            .entry(owner.to_string())
            .or_default()
    }

    fn total(&self, counter: &str) -> i32 {
        let slots = self.counters.get(counter);
        slots.map_or(0, |s| s.values().map(|slot| slot.up - slot.down).sum::<i64>()) as i32
    }

    fn tags(&mut self, set_name: &str, element: &str) -> &mut Tags {
        self.sets
            .entry(set_name.to_string())
            .or_default()
            .entry(element.to_string())
            .or_default()
    }

    fn live(&self, set_name: &str, element: &str) -> bool {
        self.sets
            .get(set_name)
            .and_then(|elements| elements.get(element))
            .is_some_and(|tags| tags.values().any(|tag| !tag.removed))
    }

    fn size(&self) -> i32 {
        let mut count = self.registers.len();
        for slots in self.counters.values() {
            for slot in slots.values() {
                count += usize::from(slot.up > 0) + usize::from(slot.down > 0);
            }
        }
        for elements in self.sets.values() {
            for tags in elements.values() {
                count += tags.values().map(|tag| 1 + usize::from(tag.removed)).sum::<usize>();
            }
        }
        count as i32
    }

    /// Joins every entry of `source` that changed after `since` and returns how many entries that
    /// was; `since = 0` is a full-state merge.
    fn absorb(&mut self, source: &Replica, since: i64) -> i32 {
        let mut sent = 0;
        for (counter, slots) in &source.counters {
            for (owner, theirs) in slots {
                if theirs.up > 0 && theirs.up_at > since {
                    sent += 1;
                    if theirs.up > self.slot(counter, owner).up {
                        let at = self.tick();
                        let mine = self.slot(counter, owner);
                        mine.up = theirs.up;
                        mine.up_at = at;
                    }
                }
                if theirs.down > 0 && theirs.down_at > since {
                    sent += 1;
                    if theirs.down > self.slot(counter, owner).down {
                        let at = self.tick();
                        let mine = self.slot(counter, owner);
                        mine.down = theirs.down;
                        mine.down_at = at;
                    }
                }
            }
        }
        for (name, theirs) in &source.registers {
            if theirs.at <= since {
                continue;
            }
            sent += 1;
            let wins = match self.registers.get(name) {
                None => true,
                Some(mine) => mine.loses_to(theirs.timestamp, &theirs.writer),
            };
            if wins {
                let at = self.tick();
                self.registers.insert(name.clone(), Register { at, ..theirs.clone() });
            }
        }
        for (set_name, elements) in &source.sets {
            for (element, tags) in elements {
                for (id, theirs) in tags {
                    sent += self.absorb_tag(set_name, element, id, theirs, since);
                }
            }
        }
        sent
    }

    fn absorb_tag(&mut self, set_name: &str, element: &str, id: &str, theirs: &Tag, since: i64) -> i32 {
        let mut sent = 0;
        if theirs.added_at > since {
            sent += 1;
            if !self.tags(set_name, element).contains_key(id) {
                let at = self.tick();
                self.tags(set_name, element).insert(id.to_string(), Tag::new(at));
            }
        }
        if theirs.removed && theirs.removed_at > since {
            sent += 1;
            if !self.tags(set_name, element).contains_key(id) {
                let at = self.tick();
                self.tags(set_name, element).insert(id.to_string(), Tag::new(at));
            }
            if !self.tags(set_name, element)[id].removed {
                let at = self.tick();
                let held = self.tags(set_name, element).get_mut(id).unwrap();
                held.removed = true;
                held.removed_at = at;
            }
        }
        sent
    }
}

/// A group of replicas of the same data. Each replica's state is a set of entries that only grow,
/// and merging is taking the larger value of every entry, so merges can happen in any order, any
/// number of times, and replicas that have seen the same updates hold the same state.
pub struct Replicas {
    replicas: HashMap<String, Replica>,
}

impl Replicas {
    pub fn new(ids: Vec<String>) -> Self {
        Replicas { replicas: ids.into_iter().map(|id| (id, Replica::default())).collect() }
    }

    fn at(&mut self, name: &str) -> &mut Replica {
        self.replicas.get_mut(name).unwrap()
    }

    /// Joins the entries of `source` changed after `since` into `target`; the two are distinct,
    /// so the target is taken out of the map while it reads the source.
    fn absorb(&mut self, source: &str, target: &str, since: i64) -> i32 {
        let mut receiver = self.replicas.remove(target).unwrap();
        let sent = receiver.absorb(&self.replicas[source], since);
        self.replicas.insert(target.to_string(), receiver);
        sent
    }

    // Level 1
    pub fn increment(&mut self, replica: String, counter: String, amount: i32) -> i32 {
        let node = self.at(&replica);
        let at = node.tick();
        let slot = node.slot(&counter, &replica);
        slot.up += i64::from(amount);
        slot.up_at = at;
        node.total(&counter)
    }

    pub fn decrement(&mut self, replica: String, counter: String, amount: i32) -> i32 {
        let node = self.at(&replica);
        let at = node.tick();
        let slot = node.slot(&counter, &replica);
        slot.down += i64::from(amount);
        slot.down_at = at;
        node.total(&counter)
    }

    pub fn value(&mut self, replica: String, counter: String) -> i32 {
        self.at(&replica).total(&counter)
    }

    pub fn merge(&mut self, source: String, target: String) {
        self.absorb(&source, &target, 0);
    }

    // Level 2
    pub fn write(&mut self, replica: String, register: String, text: String, timestamp: i64) -> bool {
        let node = self.at(&replica);
        if let Some(current) = node.registers.get(&register) {
            if !current.loses_to(timestamp, &replica) {
                return false;
            }
        }
        let at = node.tick();
        node.registers.insert(register, Register { text, timestamp, writer: replica, at });
        true
    }

    pub fn read(&mut self, replica: String, register: String) -> String {
        let node = self.at(&replica);
        node.registers.get(&register).map_or(String::new(), |current| current.text.clone())
    }

    // Level 3
    pub fn add(&mut self, replica: String, set_name: String, element: String) -> String {
        let node = self.at(&replica);
        node.adds += 1;
        let id = format!("{}:{}", replica, node.adds);
        let at = node.tick();
        node.tags(&set_name, &element).insert(id.clone(), Tag::new(at));
        id
    }

    pub fn remove(&mut self, replica: String, set_name: String, element: String) -> i32 {
        let node = self.at(&replica);
        let first = node.clock + 1;
        let mut removed = 0;
        if let Some(tags) = node.sets.get_mut(&set_name).and_then(|e| e.get_mut(&element)) {
            for tag in tags.values_mut().filter(|tag| !tag.removed) {
                tag.removed = true;
                tag.removed_at = first + removed;
                removed += 1;
            }
        }
        node.clock += removed;
        removed as i32
    }

    pub fn contains(&mut self, replica: String, set_name: String, element: String) -> bool {
        self.at(&replica).live(&set_name, &element)
    }

    pub fn elements(&mut self, replica: String, set_name: String) -> Vec<String> {
        let node = self.at(&replica);
        let mut present: Vec<String> = match node.sets.get(&set_name) {
            None => Vec::new(),
            Some(elements) => elements.keys().filter(|e| node.live(&set_name, e)).cloned().collect(),
        };
        present.sort();
        present
    }

    // Level 4
    pub fn sync(&mut self, source: String, target: String) -> i32 {
        let since = self.replicas[&source].acked.get(&target).copied().unwrap_or(0);
        let sent = self.absorb(&source, &target, since);
        let sender = self.at(&source);
        let clock = sender.clock;
        sender.acked.insert(target, clock);
        sent
    }

    pub fn state_size(&mut self, replica: String) -> i32 {
        self.at(&replica).size()
    }
}
