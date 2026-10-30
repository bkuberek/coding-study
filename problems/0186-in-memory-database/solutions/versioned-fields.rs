use std::collections::HashMap;

/// One write to a field: a value (`None` for a deletion), from `since` until `expires_at`.
struct Version {
    since: i64,
    value: Option<String>,
    expires_at: Option<i64>,
}

impl Version {
    fn visible_at(&self, moment: i64) -> bool {
        self.value.is_some()
            && match self.expires_at {
                None => true,
                Some(expires_at) => moment < expires_at,
            }
    }
}

/// Every version of one field, oldest first; timestamps arrive in increasing order.
#[derive(Default)]
struct FieldHistory {
    versions: Vec<Version>,
}

impl FieldHistory {
    fn value_at(&self, moment: i64) -> Option<&str> {
        let position = self
            .versions
            .partition_point(|version| version.since <= moment);
        let version = self.versions.get(position.checked_sub(1)?)?;
        if version.visible_at(moment) {
            version.value.as_deref()
        } else {
            None
        }
    }
}

pub struct InMemoryDatabase {
    records: HashMap<String, HashMap<String, FieldHistory>>,
}

impl InMemoryDatabase {
    pub fn new() -> Self {
        InMemoryDatabase {
            records: HashMap::new(),
        }
    }

    // Level 1
    pub fn set(&mut self, timestamp: i64, key: String, field: String, value: String) {
        let version = Version {
            since: timestamp,
            value: Some(value),
            expires_at: None,
        };
        self.write(key, field, version);
    }

    // Level 1
    pub fn get(&mut self, timestamp: i64, key: String, field: String) -> String {
        self.value_at(&key, &field, timestamp)
            .unwrap_or_default()
            .to_string()
    }

    // Level 1
    pub fn remove(&mut self, timestamp: i64, key: String, field: String) -> bool {
        if self.value_at(&key, &field, timestamp).is_none() {
            return false;
        }
        let version = Version {
            since: timestamp,
            value: None,
            expires_at: None,
        };
        self.write(key, field, version);
        true
    }

    // Level 2
    pub fn scan(&mut self, timestamp: i64, key: String) -> Vec<String> {
        self.scan_fields(&key, "", timestamp)
    }

    // Level 2
    pub fn scan_by_prefix(&mut self, timestamp: i64, key: String, prefix: String) -> Vec<String> {
        self.scan_fields(&key, &prefix, timestamp)
    }

    // Level 3
    pub fn set_with_ttl(
        &mut self,
        timestamp: i64,
        key: String,
        field: String,
        value: String,
        ttl: i64,
    ) {
        let version = Version {
            since: timestamp,
            value: Some(value),
            expires_at: Some(timestamp + ttl),
        };
        self.write(key, field, version);
    }

    // Level 4
    pub fn get_at(
        &mut self,
        timestamp: i64,
        key: String,
        field: String,
        at_timestamp: i64,
    ) -> String {
        self.value_at(&key, &field, at_timestamp)
            .unwrap_or_default()
            .to_string()
    }

    // Level 4
    pub fn scan_at(&mut self, timestamp: i64, key: String, at_timestamp: i64) -> Vec<String> {
        self.scan_fields(&key, "", at_timestamp)
    }

    fn write(&mut self, key: String, field: String, version: Version) {
        let fields = self.records.entry(key).or_default();
        fields.entry(field).or_default().versions.push(version);
    }

    fn value_at(&self, key: &str, field: &str, moment: i64) -> Option<&str> {
        self.records.get(key)?.get(field)?.value_at(moment)
    }

    fn scan_fields(&self, key: &str, prefix: &str, moment: i64) -> Vec<String> {
        let Some(fields) = self.records.get(key) else {
            return Vec::new();
        };
        let mut entries: Vec<(&str, &str)> = fields
            .iter()
            .filter(|(field, _)| field.starts_with(prefix))
            .filter_map(|(field, history)| Some((field.as_str(), history.value_at(moment)?)))
            .collect();
        entries.sort();
        entries
            .into_iter()
            .map(|(field, value)| format!("{field}({value})"))
            .collect()
    }
}
