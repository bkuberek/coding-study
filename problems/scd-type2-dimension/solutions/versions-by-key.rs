use std::collections::{BTreeMap, BTreeSet, HashMap};

const OPEN_END: i32 = 99991231;
const UNKNOWN_MEMBER: i32 = 0;

struct Version {
    key: i32,
    business_key: String,
    values: Vec<String>,
    valid_from: i32,
    valid_to: i32,
}

impl Version {
    fn row(&self) -> Vec<String> {
        let mut row = vec![self.key.to_string(), self.business_key.clone()];
        row.extend(self.values.iter().cloned());
        row.push(self.valid_from.to_string());
        row.push(self.valid_to.to_string());
        row.push(if self.valid_to == OPEN_END { "Y" } else { "N" }.to_string());
        row
    }
}

/// Every business key keeps its versions in a vector sorted by `valid_from`, and the versions never
/// overlap, so the version valid at a date is one binary search away. Versions live in one arena
/// and are referred to by index. Untracked attributes hold one value per business key, copied into
/// every version, and the date of the latest load that carried the key decides whether a row may
/// still overwrite them.
pub struct DimensionTable {
    width: usize,
    position: HashMap<String, usize>,
    tracked: Vec<usize>,
    arena: Vec<Version>,
    by_surrogate: HashMap<i32, usize>,
    versions: BTreeMap<String, Vec<usize>>,
    last_load: HashMap<String, i32>,
    next_key: i32,
}

impl DimensionTable {
    pub fn new(attributes: Vec<String>) -> Self {
        DimensionTable {
            width: attributes.len(),
            position: attributes.into_iter().enumerate().map(|(index, name)| (name, index)).collect(),
            tracked: Vec::new(),
            arena: Vec::new(),
            by_surrogate: HashMap::new(),
            versions: BTreeMap::new(),
            last_load: HashMap::new(),
            next_key: 1,
        }
    }

    // Level 1
    pub fn load(&mut self, rows: Vec<Vec<String>>, load_date: i32) -> Vec<i32> {
        self.apply(&rows, load_date).0
    }

    pub fn lookup(&mut self, business_key: String) -> i32 {
        match self.versions.get(&business_key).and_then(|list| list.last()) {
            Some(&last) if self.arena[last].valid_to == OPEN_END => self.arena[last].key,
            _ => -1,
        }
    }

    pub fn row_of(&mut self, surrogate_key: i32) -> Vec<String> {
        self.by_surrogate.get(&surrogate_key).map(|&at| self.arena[at].row()).unwrap_or_default()
    }

    pub fn size(&mut self) -> i32 {
        self.arena.len() as i32
    }

    // Level 2
    pub fn track_history(&mut self, attribute: String) -> bool {
        match self.position.get(&attribute) {
            Some(&index) if !self.tracked.contains(&index) => {
                self.tracked.push(index);
                true
            }
            _ => false,
        }
    }

    pub fn history(&mut self, business_key: String) -> Vec<Vec<String>> {
        self.versions
            .get(&business_key)
            .map(|list| list.iter().map(|&at| self.arena[at].row()).collect())
            .unwrap_or_default()
    }

    // Level 3
    pub fn lookup_at(&mut self, business_key: String, as_of: i32) -> i32 {
        self.valid_at(&business_key, as_of).map(|at| self.arena[at].key).unwrap_or(-1)
    }

    pub fn snapshot_at(&mut self, as_of: i32) -> Vec<Vec<String>> {
        self.versions
            .keys()
            .filter_map(|business_key| self.valid_at(business_key, as_of))
            .map(|at| self.arena[at].row())
            .collect()
    }

    pub fn resolve_facts(&mut self, facts: Vec<Vec<String>>) -> Vec<Vec<String>> {
        let unknown = UNKNOWN_MEMBER.to_string();
        facts
            .into_iter()
            .map(|fact| {
                let (fact_id, business_key) = (fact[0].clone(), &fact[1]);
                if !self.versions.contains_key(business_key) {
                    return vec![fact_id, unknown.clone(), "unknown-key".to_string()];
                }
                let event_date: i32 = fact[2].parse().unwrap_or(0);
                match self.valid_at(business_key, event_date) {
                    None => vec![fact_id, unknown.clone(), "no-version".to_string()],
                    Some(at) => {
                        let version = &self.arena[at];
                        let status = if version.valid_to == OPEN_END { "current" } else { "late" };
                        vec![fact_id, version.key.to_string(), status.to_string()]
                    }
                }
            })
            .collect()
    }

    // Level 4
    pub fn load_full(&mut self, rows: Vec<Vec<String>>, load_date: i32) -> Vec<i32> {
        let (mut counts, present) = self.apply(&rows, load_date);
        let mut closed = 0;
        for (business_key, list) in &self.versions {
            let last = *list.last().expect("a known key has a version");
            if !present.contains(business_key) && self.arena[last].valid_to == OPEN_END {
                self.arena[last].valid_to = load_date;
                closed += 1;
            }
        }
        counts.push(closed);
        counts
    }

    pub fn full_history(&mut self) -> Vec<Vec<String>> {
        self.versions.values().flat_map(|list| list.iter().map(|&at| self.arena[at].row())).collect()
    }

    // Helpers
    fn apply(&mut self, rows: &[Vec<String>], load_date: i32) -> (Vec<i32>, BTreeSet<String>) {
        let mut latest: BTreeMap<String, Vec<String>> = BTreeMap::new();
        for row in rows {
            latest.insert(row[0].clone(), row[1..].to_vec());
        }
        let mut counts = vec![0, 0, 0];
        for (business_key, values) in &latest {
            if !self.versions.contains_key(business_key) {
                self.versions.insert(business_key.clone(), Vec::new());
                self.last_load.insert(business_key.clone(), load_date);
                self.insert(business_key, values.clone(), load_date, OPEN_END);
                counts[0] += 1;
            } else if self.merge(business_key, values, load_date) {
                counts[1] += 1;
            } else {
                counts[2] += 1;
            }
        }
        (counts, latest.into_keys().collect())
    }

    fn merge(&mut self, business_key: &str, values: &[String], load_date: i32) -> bool {
        let list = self.versions[business_key].clone();
        let mut changed = false;
        if load_date >= self.last_load[business_key] {
            self.last_load.insert(business_key.to_string(), load_date);
            for index in (0..self.width).filter(|index| !self.tracked.contains(index)) {
                if self.arena[list[0]].values[index] != values[index] {
                    for &at in &list {
                        self.arena[at].values[index] = values[index].clone();
                    }
                    changed = true;
                }
            }
        }
        let fresh = self.combine(list[0], values);
        if let Some(holder) = self.valid_at(business_key, load_date) {
            if self.tracked.iter().all(|&index| self.arena[holder].values[index] == values[index]) {
                return changed;
            }
            if self.arena[holder].valid_from == load_date {
                for &index in &self.tracked {
                    self.arena[holder].values[index] = values[index].clone();
                }
                return true;
            }
            let end = self.arena[holder].valid_to;
            self.arena[holder].valid_to = load_date;
            self.insert(business_key, fresh, load_date, end);
            return true;
        }
        let end = list
            .iter()
            .map(|&at| self.arena[at].valid_from)
            .find(|&start| start > load_date)
            .unwrap_or(OPEN_END);
        self.insert(business_key, fresh, load_date, end);
        true
    }

    /// The incoming tracked values with the key's untracked values.
    fn combine(&self, shared: usize, values: &[String]) -> Vec<String> {
        let mut combined = self.arena[shared].values.clone();
        for &index in &self.tracked {
            combined[index] = values[index].clone();
        }
        combined
    }

    fn insert(&mut self, business_key: &str, values: Vec<String>, valid_from: i32, valid_to: i32) {
        let version = Version {
            key: self.next_key,
            business_key: business_key.to_string(),
            values,
            valid_from,
            valid_to,
        };
        self.next_key += 1;
        self.by_surrogate.insert(version.key, self.arena.len());
        self.arena.push(version);
        let new_at = self.arena.len() - 1;
        let arena = &self.arena;
        let list = self.versions.get_mut(business_key).expect("the key was registered");
        let place = list.partition_point(|&at| arena[at].valid_from <= valid_from);
        list.insert(place, new_at);
    }

    fn valid_at(&self, business_key: &str, as_of: i32) -> Option<usize> {
        let list = self.versions.get(business_key)?;
        let place = list.partition_point(|&at| self.arena[at].valid_from <= as_of);
        if place == 0 {
            return None;
        }
        let at = list[place - 1];
        if as_of >= self.arena[at].valid_to {
            None
        } else {
            Some(at)
        }
    }
}
