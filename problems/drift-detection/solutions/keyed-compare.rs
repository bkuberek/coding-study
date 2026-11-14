use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};

type Attributes = BTreeMap<String, String>;

struct Entry {
    tag: String,
    attributes: Attributes,
}

fn to_map(attributes: Vec<Vec<String>>) -> Attributes {
    attributes.into_iter().map(|pair| (pair[0].clone(), pair[1].clone())).collect()
}

fn kind_of(address: &str) -> &str {
    address.split('.').next().unwrap_or("")
}

fn row(parts: &[&str]) -> Vec<String> {
    parts.iter().map(|part| part.to_string()).collect()
}

/// Whether `text` matches `pattern`, where `*` stands for any run of characters. On a mismatch,
/// go back to the last star and let it swallow one more character.
fn glob(pattern: &str, text: &str) -> bool {
    let (pattern, text) = (pattern.as_bytes(), text.as_bytes());
    let (mut p, mut t) = (0, 0);
    let (mut star, mut mark): (Option<usize>, usize) = (None, 0);
    while t < text.len() {
        if p < pattern.len() && pattern[p] != b'*' && pattern[p] == text[t] {
            p += 1;
            t += 1;
        } else if p < pattern.len() && pattern[p] == b'*' {
            star = Some(p);
            mark = t;
            p += 1;
        } else if let Some(at) = star {
            mark += 1;
            p = at + 1;
            t = mark;
        } else {
            return false;
        }
    }
    while p < pattern.len() && pattern[p] == b'*' {
        p += 1;
    }
    p == pattern.len()
}

/// The recorded state maps an address to an id and attributes, and a scan maps an id to a type
/// and attributes. Drift is found by looking each recorded id up in the scan, comparing values
/// after the type's normalization rules, and filtering the rows through the ignore rules. Import
/// adds a recorded entry, the plan compares the desired state with the recorded one, and a
/// reconcile turns each drift row into the action of the newest policy that matches.
pub struct DriftDetector {
    recorded: HashMap<String, Entry>,
    observed: HashMap<String, Entry>,
    ignores: Vec<(String, String)>,
    lists: HashSet<(String, String)>,
    defaults: HashMap<(String, String), String>,
    desired: HashMap<String, Attributes>,
    policies: Vec<(String, String)>,
}

impl DriftDetector {
    pub fn new() -> Self {
        DriftDetector {
            recorded: HashMap::new(),
            observed: HashMap::new(),
            ignores: Vec::new(),
            lists: HashSet::new(),
            defaults: HashMap::new(),
            desired: HashMap::new(),
            policies: Vec::new(),
        }
    }

    // Level 1
    pub fn record(&mut self, address: String, resource_id: String, attributes: Vec<Vec<String>>) -> bool {
        let entry = Entry { tag: resource_id, attributes: to_map(attributes) };
        self.recorded.insert(address, entry).is_none()
    }

    pub fn observe(&mut self, resource_id: String, resource_type: String, attributes: Vec<Vec<String>>) -> bool {
        let entry = Entry { tag: resource_type, attributes: to_map(attributes) };
        self.observed.insert(resource_id, entry).is_none()
    }

    pub fn drift(&mut self) -> Vec<Vec<String>> {
        self.drift_rows().into_iter().map(|(line, _)| line).collect()
    }

    // Level 2
    pub fn ignore(&mut self, pattern: String, key: String) -> bool {
        if self.ignores.iter().any(|(p, k)| *p == pattern && *k == key) {
            return false;
        }
        self.ignores.push((pattern, key));
        true
    }

    pub fn unordered(&mut self, resource_type: String, key: String) -> bool {
        self.lists.insert((resource_type, key))
    }

    pub fn default_value(&mut self, resource_type: String, key: String, value: String) -> bool {
        self.defaults.insert((resource_type, key), value).is_none()
    }

    // Level 3
    pub fn import_resource(&mut self, address: String, resource_id: String) -> String {
        let Some(found) = self.observed.get(&resource_id) else {
            return "not-found".to_string();
        };
        if kind_of(&address) != found.tag {
            return "type-mismatch".to_string();
        }
        if self.recorded.values().any(|entry| entry.tag == resource_id) {
            return "already-managed".to_string();
        }
        if self.recorded.contains_key(&address) {
            return "address-taken".to_string();
        }
        let attributes = found.attributes.clone();
        self.recorded.insert(address, Entry { tag: resource_id, attributes });
        "imported".to_string()
    }

    pub fn desire(&mut self, address: String, attributes: Vec<Vec<String>>) -> bool {
        self.desired.insert(address, to_map(attributes)).is_none()
    }

    pub fn plan(&mut self) -> Vec<Vec<String>> {
        let addresses: BTreeSet<&String> = self.desired.keys().chain(self.recorded.keys()).collect();
        let mut rows = Vec::new();
        for address in addresses {
            match (self.recorded.get(address), self.desired.get(address)) {
                (None, _) => rows.push(row(&["create", address])),
                (Some(_), None) => rows.push(row(&["delete", address])),
                (Some(entry), Some(wanted)) => {
                    for key in self.differing(kind_of(address), &entry.attributes, wanted) {
                        let old = entry.attributes.get(&key).map_or("", |v| v.as_str());
                        let new = wanted.get(&key).map_or("", |v| v.as_str());
                        rows.push(row(&["update", address, &key, old, new]));
                    }
                }
            }
        }
        rows
    }

    // Level 4
    pub fn policy(&mut self, pattern: String, mode: String) -> bool {
        let before = self.policies.len();
        self.policies.retain(|(p, _)| *p != pattern);
        let is_new = self.policies.len() == before;
        self.policies.push((pattern, mode));
        is_new
    }

    pub fn reconcile(&mut self) -> Vec<Vec<String>> {
        let mut rows = Vec::new();
        for (line, address) in self.drift_rows() {
            if line[0] == "unmanaged" {
                rows.push(row(&["alert-unmanaged", &line[1], &line[2]]));
                continue;
            }
            let mode = self.mode(&address);
            if line[0] == "deleted" {
                rows.push(match mode {
                    "revert" => row(&["recreate", &address]),
                    "accept" => row(&["forget", &address]),
                    _ => row(&["alert-deleted", &address, &line[2]]),
                });
                continue;
            }
            let (key, recorded, scanned) = (&line[2], &line[3], &line[4]);
            if mode == "alert" {
                rows.push(row(&["alert", &address, key, recorded, scanned]));
                continue;
            }
            let wanted = self.desired.get(&address).and_then(|d| d.get(key)).cloned().unwrap_or_default();
            let present = |value: &String| if value.is_empty() { None } else { Some(value.clone()) };
            if self.same(kind_of(&address), key, present(scanned), present(&wanted)) {
                continue;
            }
            if mode == "revert" {
                rows.push(row(&["revert", &address, key, scanned, &wanted]));
            } else {
                rows.push(row(&["accept", &address, key, &wanted, scanned]));
            }
        }
        rows
    }

    // Comparing
    fn same(&self, resource_type: &str, key: &str, first: Option<String>, second: Option<String>) -> bool {
        let id = (resource_type.to_string(), key.to_string());
        let fallback = self.defaults.get(&id).cloned();
        let a = first.or_else(|| fallback.clone());
        let b = second.or(fallback);
        match (a, b) {
            (Some(a), Some(b)) => {
                if self.lists.contains(&id) {
                    let mut left: Vec<&str> = a.split(',').collect();
                    let mut right: Vec<&str> = b.split(',').collect();
                    left.sort_unstable();
                    right.sort_unstable();
                    left == right
                } else {
                    a == b
                }
            }
            (a, b) => a == b,
        }
    }

    fn differing(&self, resource_type: &str, first: &Attributes, second: &Attributes) -> Vec<String> {
        let keys: BTreeSet<&String> = first.keys().chain(second.keys()).collect();
        keys.into_iter()
            .filter(|key| !self.same(resource_type, key, first.get(*key).cloned(), second.get(*key).cloned()))
            .cloned()
            .collect()
    }

    fn ignored(&self, text: &str, key: &str) -> bool {
        self.ignores.iter().any(|(pattern, rule_key)| rule_key == key && glob(pattern, text))
    }

    fn mode(&self, address: &str) -> &str {
        self.policies
            .iter()
            .rev()
            .find(|(pattern, _)| glob(pattern, address))
            .map_or("alert", |(_, mode)| mode.as_str())
    }

    /// The drift rows, each with the address it is about ("" for an unmanaged resource).
    fn drift_rows(&self) -> Vec<(Vec<String>, String)> {
        let mut rows = Vec::new();
        let mut managed = HashSet::new();
        let addresses: BTreeSet<&String> = self.recorded.keys().collect();
        for address in addresses {
            let entry = &self.recorded[address];
            managed.insert(entry.tag.clone());
            if self.ignored(address, "*") {
                continue;
            }
            let Some(found) = self.observed.get(&entry.tag) else {
                rows.push((row(&["deleted", address, &entry.tag]), address.clone()));
                continue;
            };
            for key in self.differing(kind_of(address), &entry.attributes, &found.attributes) {
                if !self.ignored(address, &key) {
                    let ours = entry.attributes.get(&key).map_or("", |v| v.as_str());
                    let theirs = found.attributes.get(&key).map_or("", |v| v.as_str());
                    rows.push((row(&["changed", address, &key, ours, theirs]), address.clone()));
                }
            }
        }
        let ids: BTreeSet<&String> = self.observed.keys().collect();
        for resource_id in ids {
            let resource_type = &self.observed[resource_id].tag;
            if !managed.contains(resource_id) && !self.ignored(&format!("{resource_type}.{resource_id}"), "*") {
                rows.push((row(&["unmanaged", resource_id, resource_type]), String::new()));
            }
        }
        rows
    }
}
