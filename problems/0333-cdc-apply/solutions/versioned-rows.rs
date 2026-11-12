use std::collections::{BTreeSet, HashMap};

const OK: &str = "ok";
const SKIPPED: &str = "skipped";
const NEVER: i32 = -1;

/// A map from key to row holds the table. A second map holds each key's version, the position at
/// which its last change became visible, and keeps it when the row is deleted: that tombstone is
/// what stops an old insert from bringing a deleted row back.
///
/// A change is skipped when its position is not after the key's version, or not after the
/// snapshot the table started from. A transaction's changes wait in a buffer until its commit,
/// then run into an overlay, a small map of the rows they change, which is written into the
/// table only when every change worked.
pub struct ReplicaTable {
    names: Vec<String>,
    table: HashMap<String, Vec<String>>,
    versions: HashMap<String, i32>,
    floor: i32,
    schema_version: i32,
    staged: HashMap<String, Vec<(String, Vec<String>)>>,
}

impl ReplicaTable {
    pub fn new(columns: Vec<String>) -> Self {
        ReplicaTable {
            names: columns,
            table: HashMap::new(),
            versions: HashMap::new(),
            floor: 0,
            schema_version: 0,
            staged: HashMap::new(),
        }
    }

    // Level 1
    pub fn apply(&mut self, op: String, row: Vec<String>) -> String {
        let code = self.check(self.table.contains_key(&row[0]), &op, &row);
        if code == OK {
            if op == "delete" {
                self.table.remove(&row[0]);
            } else {
                self.table.insert(row[0].clone(), row);
            }
        }
        code.to_string()
    }

    pub fn rows(&mut self) -> Vec<Vec<String>> {
        let mut keys: Vec<&String> = self.table.keys().collect();
        keys.sort();
        keys.into_iter()
            .map(|key| self.table[key].clone())
            .collect()
    }

    // Level 2
    pub fn apply_at(&mut self, lsn: i32, op: String, row: Vec<String>) -> String {
        let key = row[0].clone();
        if lsn <= self.floor || lsn <= self.version(key.clone()) {
            return SKIPPED.to_string();
        }
        let code = self.apply(op, row);
        if code == OK {
            self.versions.insert(key, lsn);
        }
        code
    }

    pub fn version(&mut self, key: String) -> i32 {
        *self.versions.get(&key).unwrap_or(&NEVER)
    }

    // Level 3
    pub fn load_snapshot(&mut self, lsn: i32, snapshot: Vec<Vec<String>>) {
        self.versions = snapshot.iter().map(|row| (row[0].clone(), lsn)).collect();
        self.table = snapshot
            .into_iter()
            .map(|row| (row[0].clone(), row))
            .collect();
        self.floor = lsn;
    }

    pub fn stage(&mut self, tx: String, op: String, row: Vec<String>) {
        self.staged.entry(tx).or_default().push((op, row));
    }

    pub fn commit(&mut self, lsn: i32, tx: String) -> String {
        let changes = self.staged.remove(&tx).unwrap_or_default();
        if lsn <= self.floor {
            return SKIPPED.to_string();
        }
        // None marks a key that this transaction deleted; `order` keeps the keys in first-touch order.
        let mut overlay: HashMap<String, Option<Vec<String>>> = HashMap::new();
        let mut order: Vec<String> = Vec::new();
        for (op, row) in changes {
            let key = row[0].clone();
            if lsn <= *self.versions.get(&key).unwrap_or(&NEVER) {
                continue;
            }
            let present = match overlay.get(&key) {
                Some(pending) => pending.is_some(),
                None => {
                    order.push(key.clone());
                    self.table.contains_key(&key)
                }
            };
            let code = self.check(present, &op, &row);
            if code != OK {
                return code.to_string();
            }
            overlay.insert(key, if op == "delete" { None } else { Some(row) });
        }
        if order.is_empty() {
            return SKIPPED.to_string();
        }
        for key in order {
            match overlay.remove(&key).flatten() {
                Some(row) => {
                    self.table.insert(key.clone(), row);
                }
                None => {
                    self.table.remove(&key);
                }
            }
            self.versions.insert(key, lsn);
        }
        OK.to_string()
    }

    pub fn rollback(&mut self, tx: String) {
        self.staged.remove(&tx);
    }

    // Level 4
    pub fn alter_at(&mut self, lsn: i32, change: Vec<String>) -> String {
        if lsn <= self.floor || lsn <= self.schema_version {
            return SKIPPED.to_string();
        }
        let code = self.alter(&change);
        if code == OK {
            self.schema_version = lsn;
        }
        code.to_string()
    }

    pub fn columns(&mut self) -> Vec<String> {
        self.names.clone()
    }

    pub fn compare(
        &mut self,
        source_columns: Vec<String>,
        source_rows: Vec<Vec<String>>,
    ) -> Vec<Vec<String>> {
        let mut report: Vec<Vec<String>> = Vec::new();
        let all: BTreeSet<&String> = self.names.iter().chain(source_columns.iter()).collect();
        for name in &all {
            if !self.names.contains(name) {
                report.push(vec!["missing-column".to_string(), (*name).clone()]);
            } else if !source_columns.contains(name) {
                report.push(vec!["extra-column".to_string(), (*name).clone()]);
            }
        }
        let common: Vec<&String> = all
            .into_iter()
            .filter(|name| self.names.contains(name) && source_columns.contains(name))
            .collect();
        let source: HashMap<&String, &Vec<String>> =
            source_rows.iter().map(|row| (&row[0], row)).collect();
        let keys: BTreeSet<&String> = self.table.keys().chain(source.keys().copied()).collect();
        for key in keys {
            match (self.table.get(key), source.get(key)) {
                (None, _) => report.push(vec!["missing-row".to_string(), key.clone()]),
                (_, None) => report.push(vec!["extra-row".to_string(), key.clone()]),
                (Some(here), Some(there)) => {
                    for name in &common {
                        let a = &here[self.names.iter().position(|n| n == *name).unwrap()];
                        let b = &there[source_columns.iter().position(|n| n == *name).unwrap()];
                        if a != b {
                            report.push(vec![
                                "value-differs".to_string(),
                                key.clone(),
                                (*name).clone(),
                                a.clone(),
                                b.clone(),
                            ]);
                        }
                    }
                }
            }
        }
        report
    }

    // Changes
    fn check(&self, present: bool, op: &str, row: &[String]) -> &'static str {
        if op != "delete" && row.len() != self.names.len() {
            return "column-count";
        }
        match (op, present) {
            ("insert", true) => "duplicate-key",
            ("insert", false) => OK,
            (_, true) => OK,
            (_, false) => "unknown-key",
        }
    }

    fn alter(&mut self, change: &[String]) -> &'static str {
        let (kind, name) = (change[0].as_str(), &change[1]);
        if kind == "add" {
            if self.names.contains(name) {
                return "duplicate-column";
            }
            self.names.push(name.clone());
            for row in self.table.values_mut() {
                row.push(change[2].clone());
            }
            return OK;
        }
        let Some(index) = self.names.iter().position(|n| n == name) else {
            return "unknown-column";
        };
        if kind == "drop" {
            if index == 0 {
                return "key-column";
            }
            self.names.remove(index);
            for row in self.table.values_mut() {
                row.remove(index);
            }
            return OK;
        }
        if self.names.contains(&change[2]) {
            return "duplicate-column";
        }
        self.names[index] = change[2].clone();
        OK
    }
}
