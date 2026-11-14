use std::collections::{BTreeSet, HashMap, HashSet};

#[derive(Clone, Copy, PartialEq)]
enum State {
    Active,
    Committed,
    Aborted,
}

struct Transaction {
    start: i32,
    serializable: bool,
    state: State,
    commit_time: i32,
    writes: Vec<(String, String)>,
    ins: BTreeSet<i32>,
    outs: BTreeSet<i32>,
}

impl Transaction {
    fn written(&self, key: &str) -> Option<&String> {
        self.writes.iter().find(|(k, _)| k == key).map(|(_, value)| value)
    }
}

#[derive(Default)]
struct Chain {
    stamps: Vec<i32>,
    values: Vec<String>,
    writers: Vec<i32>,
}

impl Chain {
    /// The number of versions stamped before `time`.
    fn before(&self, time: i32) -> usize {
        self.stamps.partition_point(|&stamp| stamp < time)
    }
}

/// Every key keeps a chain of committed versions, oldest first, each stamped with the commit time
/// of its writer and the id of that writer (0 for a put). A transaction buffers its writes until it
/// commits, so the chains only ever hold committed data, and a read is a binary search for the
/// newest stamp before the reader's start.
///
/// Serializable transactions also leave their reads behind, even after they commit, and every
/// read-write antidependency between two of them is kept as a pair of edges. An edge stops counting
/// as soon as either end aborts. The checks first collect the ids involved with shared borrows,
/// and only then change the transaction records.
pub struct MvccStore {
    clock: i32,
    chains: HashMap<String, Chain>,
    transactions: HashMap<i32, Transaction>,
    readers: HashMap<String, HashSet<i32>>,
}

impl MvccStore {
    pub fn new() -> Self {
        MvccStore {
            clock: 0,
            chains: HashMap::new(),
            transactions: HashMap::new(),
            readers: HashMap::new(),
        }
    }

    // Level 1
    pub fn put(&mut self, key: String, value: String) -> i32 {
        self.clock += 1;
        self.append(key, value, self.clock, 0);
        self.clock
    }

    pub fn begin(&mut self) -> i32 {
        self.start(false)
    }

    pub fn read(&mut self, tx: i32, key: String) -> String {
        let Some(reader) = self.active(tx) else { return String::new() };
        if let Some(value) = reader.written(&key) {
            return value.clone();
        }
        let (start, serializable) = (reader.start, reader.serializable);
        if serializable && !self.record_read(tx, &key) {
            return String::new();
        }
        match self.chains.get(&key) {
            Some(chain) => match chain.before(start) {
                0 => String::new(),
                visible => chain.values[visible - 1].clone(),
            },
            None => String::new(),
        }
    }

    pub fn versions(&mut self, key: String) -> Vec<String> {
        match self.chains.get(&key) {
            Some(chain) => chain
                .stamps
                .iter()
                .zip(&chain.values)
                .rev()
                .map(|(stamp, value)| format!("{stamp}:{value}"))
                .collect(),
            None => Vec::new(),
        }
    }

    // Level 2
    pub fn write(&mut self, tx: i32, key: String, value: String) -> bool {
        let Some(writer) = self.active(tx) else { return false };
        if writer.serializable && !self.record_write(tx, &key) {
            return false;
        }
        let writes = &mut self.transactions.get_mut(&tx).unwrap().writes;
        match writes.iter_mut().find(|(k, _)| *k == key) {
            Some(entry) => entry.1 = value,
            None => writes.push((key, value)),
        }
        true
    }

    pub fn commit(&mut self, tx: i32) -> String {
        let Some(t) = self.active(tx) else { return "not-active".to_string() };
        let conflict = t.writes.iter().any(|(key, _)| {
            self.chains.get(key).is_some_and(|chain| *chain.stamps.last().unwrap() > t.start)
        });
        let pivot = t.serializable && !self.live(&t.ins).is_empty() && !self.live(&t.outs).is_empty();
        if conflict || pivot {
            self.transactions.get_mut(&tx).unwrap().state = State::Aborted;
            let refusal = if conflict { "write-conflict" } else { "dangerous-structure" };
            return refusal.to_string();
        }
        self.clock += 1;
        let stamp = self.clock;
        let t = self.transactions.get_mut(&tx).unwrap();
        t.state = State::Committed;
        t.commit_time = stamp;
        let writes = t.writes.clone();
        for (key, value) in writes {
            self.append(key, value, stamp, tx);
        }
        "committed".to_string()
    }

    pub fn abort(&mut self, tx: i32) -> bool {
        if self.active(tx).is_none() {
            return false;
        }
        self.transactions.get_mut(&tx).unwrap().state = State::Aborted;
        true
    }

    pub fn status(&mut self, tx: i32) -> String {
        match self.transactions.get(&tx).map(|t| t.state) {
            Some(State::Active) => "active",
            Some(State::Committed) => "committed",
            Some(State::Aborted) => "aborted",
            None => "unknown",
        }
        .to_string()
    }

    // Level 3
    pub fn begin_serializable(&mut self) -> i32 {
        self.start(true)
    }

    pub fn antidependencies(&mut self, tx: i32) -> Vec<String> {
        match self.transactions.get(&tx) {
            Some(t) if t.state != State::Aborted => {
                let ins = self.live(&t.ins).into_iter().map(|other| format!("in:{other}"));
                let outs = self.live(&t.outs).into_iter().map(|other| format!("out:{other}"));
                ins.chain(outs).collect()
            }
            _ => Vec::new(),
        }
    }

    // Level 4
    pub fn horizon(&mut self) -> i32 {
        self.transactions
            .values()
            .filter(|t| t.state == State::Active)
            .map(|t| t.start)
            .min()
            .unwrap_or(self.clock)
    }

    pub fn vacuum(&mut self) -> Vec<String> {
        let limit = self.horizon();
        let mut keys: Vec<String> = self.chains.keys().cloned().collect();
        keys.sort();
        let mut removed = Vec::new();
        for key in keys {
            let chain = self.chains.get_mut(&key).unwrap();
            let keep_from = chain.before(limit + 1);
            if keep_from <= 1 {
                continue;
            }
            for stamp in chain.stamps.drain(..keep_from - 1) {
                removed.push(format!("{key}@{stamp}"));
            }
            chain.values.drain(..keep_from - 1);
            chain.writers.drain(..keep_from - 1);
        }
        removed
    }

    // Helpers
    fn start(&mut self, serializable: bool) -> i32 {
        self.clock += 1;
        let transaction = Transaction {
            start: self.clock,
            serializable,
            state: State::Active,
            commit_time: 0,
            writes: Vec::new(),
            ins: BTreeSet::new(),
            outs: BTreeSet::new(),
        };
        self.transactions.insert(self.clock, transaction);
        self.clock
    }

    fn active(&self, tx: i32) -> Option<&Transaction> {
        self.transactions.get(&tx).filter(|t| t.state == State::Active)
    }

    fn append(&mut self, key: String, value: String, stamp: i32, writer: i32) {
        let chain = self.chains.entry(key).or_default();
        chain.stamps.push(stamp);
        chain.values.push(value);
        chain.writers.push(writer);
    }

    fn takes_part(&self, tx: i32) -> bool {
        self.transactions.get(&tx).is_some_and(|t| t.serializable && t.state != State::Aborted)
    }

    /// The ids whose transaction has not aborted, in increasing order.
    fn live(&self, ids: &BTreeSet<i32>) -> Vec<i32> {
        ids.iter().copied().filter(|other| self.transactions[other].state != State::Aborted).collect()
    }

    /// The reader misses every version committed after it began and every write still buffered by
    /// an active transaction: each such writer gets an edge from the reader.
    fn record_read(&mut self, tx: i32, key: &str) -> bool {
        let start = self.transactions[&tx].start;
        let committed: Vec<i32> = match self.chains.get(key) {
            Some(chain) => chain.writers[chain.before(start)..]
                .iter()
                .copied()
                .filter(|&writer| self.takes_part(writer))
                .collect(),
            None => Vec::new(),
        };
        if committed.iter().any(|w| !self.live(&self.transactions[w].outs).is_empty()) {
            self.transactions.get_mut(&tx).unwrap().state = State::Aborted;
            return false;
        }
        let buffered: Vec<i32> = self
            .transactions
            .iter()
            .filter(|(&other, t)| {
                other != tx && t.serializable && t.state == State::Active && t.written(key).is_some()
            })
            .map(|(&other, _)| other)
            .collect();
        self.readers.entry(key.to_string()).or_default().insert(tx);
        for writer in committed.into_iter().chain(buffered) {
            self.edge(tx, writer);
        }
        true
    }

    /// Every reader of the key that overlaps the writer gets an edge to it.
    fn record_write(&mut self, tx: i32, key: &str) -> bool {
        let start = self.transactions[&tx].start;
        let overlapping: Vec<i32> = match self.readers.get(key) {
            Some(readers) => readers
                .iter()
                .copied()
                .filter(|&other| other != tx && self.takes_part(other))
                .filter(|other| {
                    let t = &self.transactions[other];
                    t.state == State::Active || t.commit_time > start
                })
                .collect(),
            None => Vec::new(),
        };
        let pivot_committed = overlapping.iter().any(|other| {
            let t = &self.transactions[other];
            t.state == State::Committed && !self.live(&t.ins).is_empty()
        });
        if pivot_committed {
            self.transactions.get_mut(&tx).unwrap().state = State::Aborted;
            return false;
        }
        for reader in overlapping {
            self.edge(reader, tx);
        }
        true
    }

    fn edge(&mut self, reader: i32, writer: i32) {
        self.transactions.get_mut(&reader).unwrap().outs.insert(writer);
        self.transactions.get_mut(&writer).unwrap().ins.insert(reader);
    }
}
