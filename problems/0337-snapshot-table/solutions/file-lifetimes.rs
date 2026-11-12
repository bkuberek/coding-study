use std::collections::{HashMap, HashSet};

const NEVER: i32 = i32::MAX;

struct DataFile {
    path: String,
    partition: String,
    rows: String,
    added: i32,
    removed: i32,
}

impl DataFile {
    fn live_at(&self, snapshot: i32) -> bool {
        self.added <= snapshot && snapshot < self.removed
    }
}

struct Snapshot {
    id: i32,
    parent: i32,
    timestamp: i64,
    operation: String,
    added: Vec<usize>,
    removed: Vec<usize>,
}

/// Snapshots are numbered 1, 2, 3 in commit order, and history is a single line, so a data file is
/// live in one interval of snapshots: from the one that added it up to, not including, the one that
/// removed it. Files live in one vector and are referred to by index; each keeps its interval, each
/// snapshot keeps the files it added and removed, and every question is a filter over the files or
/// a walk over the snapshots.
pub struct SnapshotTable {
    files: Vec<DataFile>,
    by_path: HashMap<String, usize>,
    snapshots: Vec<Snapshot>,
    first_retained: i32,
}

impl SnapshotTable {
    pub fn new() -> Self {
        SnapshotTable { files: Vec::new(), by_path: HashMap::new(), snapshots: Vec::new(), first_retained: 1 }
    }

    // Level 1
    pub fn append(&mut self, files: Vec<Vec<String>>, timestamp: i64) -> i32 {
        if files.is_empty() || !self.fresh(&files) {
            return -1;
        }
        self.commit_change(&files, &[], timestamp, None)
    }

    pub fn current_snapshot(&mut self) -> i32 {
        self.current()
    }

    pub fn scan(&mut self) -> Vec<String> {
        self.live_paths(self.current())
    }

    pub fn manifest(&mut self, snapshot_id: i32) -> Vec<Vec<String>> {
        if !self.retained(snapshot_id) {
            return Vec::new();
        }
        let mut entries: Vec<Vec<String>> = self
            .files
            .iter()
            .filter_map(|file| {
                let status = if file.live_at(snapshot_id) {
                    if file.added == snapshot_id { "added" } else { "existing" }
                } else if file.removed == snapshot_id {
                    "deleted"
                } else {
                    return None;
                };
                Some(vec![file.path.clone(), file.partition.clone(), file.rows.clone(), status.to_string()])
            })
            .collect();
        entries.sort();
        entries
    }

    // Level 2
    pub fn delete_files(&mut self, paths: Vec<String>, timestamp: i64) -> i32 {
        if paths.is_empty() || !self.removable(&paths, self.current()) {
            return -1;
        }
        self.commit_change(&[], &paths, timestamp, None)
    }

    pub fn overwrite(&mut self, partition: String, files: Vec<Vec<String>>, timestamp: i64) -> i32 {
        if files.iter().any(|file| file[1] != partition) || !self.fresh(&files) {
            return -1;
        }
        let current = self.current();
        let old: Vec<String> = self
            .files
            .iter()
            .filter(|file| file.partition == partition && file.live_at(current))
            .map(|file| file.path.clone())
            .collect();
        if old.is_empty() && files.is_empty() {
            return -1;
        }
        self.commit_change(&files, &old, timestamp, None)
    }

    pub fn scan_at(&mut self, snapshot_id: i32) -> Vec<String> {
        self.live_paths(snapshot_id)
    }

    pub fn snapshot_as_of(&mut self, timestamp: i64) -> i32 {
        let found = self.snapshots.iter().filter(|s| s.timestamp <= timestamp).map(|s| s.id).last().unwrap_or(0);
        if found >= self.first_retained {
            found
        } else {
            0
        }
    }

    pub fn history(&mut self) -> Vec<Vec<String>> {
        self.snapshots[(self.first_retained - 1) as usize..]
            .iter()
            .map(|s| {
                vec![
                    s.id.to_string(),
                    s.parent.to_string(),
                    s.timestamp.to_string(),
                    s.operation.clone(),
                    s.added.len().to_string(),
                    s.removed.len().to_string(),
                ]
            })
            .collect()
    }

    // Level 3
    pub fn commit(&mut self, base: i32, adds: Vec<Vec<String>>, removes: Vec<String>, timestamp: i64) -> Vec<String> {
        let current = self.current();
        let base_ok = (base == 0 && self.first_retained == 1) || self.retained(base);
        if !base_ok || (adds.is_empty() && removes.is_empty()) || !self.fresh(&adds) || !self.removable(&removes, base) {
            return vec!["invalid".to_string(), String::new()];
        }
        let removing: HashSet<usize> = removes.iter().map(|path| self.by_path[path]).collect();
        let partitions: HashSet<&str> = removing.iter().map(|&at| self.files[at].partition.as_str()).collect();
        for s in &self.snapshots[base as usize..current as usize] {
            let removed_twice = s.removed.iter().any(|at| removing.contains(at));
            let appended =
                s.operation != "replace" && s.added.iter().any(|&at| partitions.contains(self.files[at].partition.as_str()));
            if removed_twice || appended {
                return vec!["conflict".to_string(), s.id.to_string()];
            }
        }
        let outcome = if base == current { "committed" } else { "rebased" };
        let id = self.commit_change(&adds, &removes, timestamp, None);
        vec![outcome.to_string(), id.to_string()]
    }

    // Level 4
    pub fn expire_snapshots(&mut self, older_than: i64, retain_last: i32) -> Vec<String> {
        let old_first = self.first_retained;
        let last_candidate = self.current() - retain_last;
        while self.first_retained <= last_candidate
            && self.snapshots[(self.first_retained - 1) as usize].timestamp < older_than
        {
            self.first_retained += 1;
        }
        let new_first = self.first_retained;
        let mut freed: Vec<String> = self
            .files
            .iter()
            .filter(|file| old_first < file.removed && file.removed <= new_first)
            .map(|file| file.path.clone())
            .collect();
        freed.sort();
        freed
    }

    pub fn compact(&mut self, partition: String, max_file_rows: i32, timestamp: i64) -> i32 {
        let current = self.current();
        let small: Vec<&DataFile> = self
            .files
            .iter()
            .filter(|file| {
                file.partition == partition
                    && file.live_at(current)
                    && file.rows.parse::<i64>().unwrap_or(0) < i64::from(max_file_rows)
            })
            .collect();
        if small.len() < 2 {
            return -1;
        }
        let rows: i64 = small.iter().map(|file| file.rows.parse::<i64>().unwrap_or(0)).sum();
        let removes: Vec<String> = small.iter().map(|file| file.path.clone()).collect();
        let path = format!("{}/compacted-{}", partition, current + 1);
        let adds = vec![vec![path, partition, rows.to_string()]];
        self.commit_change(&adds, &removes, timestamp, Some("replace"))
    }

    // Helpers
    fn current(&self) -> i32 {
        self.snapshots.len() as i32
    }

    fn retained(&self, snapshot_id: i32) -> bool {
        self.first_retained <= snapshot_id && snapshot_id <= self.current()
    }

    fn live_paths(&self, snapshot_id: i32) -> Vec<String> {
        if !self.retained(snapshot_id) {
            return Vec::new();
        }
        let mut paths: Vec<String> =
            self.files.iter().filter(|file| file.live_at(snapshot_id)).map(|file| file.path.clone()).collect();
        paths.sort();
        paths
    }

    fn fresh(&self, adds: &[Vec<String>]) -> bool {
        let mut seen = HashSet::new();
        adds.iter().all(|file| !self.by_path.contains_key(&file[0]) && seen.insert(file[0].as_str()))
    }

    fn removable(&self, paths: &[String], snapshot_id: i32) -> bool {
        let mut seen = HashSet::new();
        paths.iter().all(|path| {
            seen.insert(path.as_str())
                && self.by_path.get(path).is_some_and(|&at| self.files[at].live_at(snapshot_id))
        })
    }

    fn commit_change(&mut self, adds: &[Vec<String>], removes: &[String], timestamp: i64, operation: Option<&str>) -> i32 {
        let parent = self.current();
        let id = parent + 1;
        let kind = operation.unwrap_or(match (adds.is_empty(), removes.is_empty()) {
            (false, false) => "overwrite",
            (false, true) => "append",
            _ => "delete",
        });
        let mut snapshot = Snapshot {
            id,
            parent,
            timestamp,
            operation: kind.to_string(),
            added: Vec::new(),
            removed: Vec::new(),
        };
        for path in removes {
            let at = self.by_path[path];
            self.files[at].removed = id;
            snapshot.removed.push(at);
        }
        for add in adds {
            self.by_path.insert(add[0].clone(), self.files.len());
            snapshot.added.push(self.files.len());
            self.files.push(DataFile {
                path: add[0].clone(),
                partition: add[1].clone(),
                rows: add[2].clone(),
                added: id,
                removed: NEVER,
            });
        }
        self.snapshots.push(snapshot);
        id
    }
}
