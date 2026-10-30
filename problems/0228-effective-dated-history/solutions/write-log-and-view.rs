use std::collections::{BTreeMap, HashMap};

use chrono::NaiveDate;

struct Write {
    time: i64,
    date: NaiveDate,
    value: String,
}

#[derive(Default)]
struct FieldHistory {
    /// Every write, in timestamp order (timestamps are sorted and distinct).
    writes: Vec<Write>,
    /// The current view: one value per effective date. A correction replaces the value for its date.
    view: BTreeMap<NaiveDate, String>,
}

impl FieldHistory {
    fn write(&mut self, time: i64, date: NaiveDate, value: String) {
        self.view.insert(date, value.clone());
        self.writes.push(Write { time, date, value });
    }

    /// The value of the last view entry on or before the day, or `""` when there is none.
    fn current(&self, on_date: NaiveDate) -> String {
        self.view
            .range(..=on_date)
            .next_back()
            .map(|(_, value)| value.clone())
            .unwrap_or_default()
    }

    /// Replays the writes made at or before `known_at`: the one with the latest effective date on
    /// or before the day wins, and a later write wins a tie on the date.
    fn as_known(&self, on_date: NaiveDate, known_at: i64) -> String {
        let known = self.writes.partition_point(|write| write.time <= known_at);
        let mut best_date: Option<NaiveDate> = None;
        let mut best_value = "";
        for write in &self.writes[..known] {
            // `None` orders before every `Some`, so the first qualifying write always wins, and
            // `>=` lets a later write for the same date replace an earlier one.
            if write.date <= on_date && Some(write.date) >= best_date {
                best_date = Some(write.date);
                best_value = &write.value;
            }
        }
        best_value.to_string()
    }
}

pub struct RecordHistory {
    /// A `BTreeMap` per record iterates the field names in sorted order.
    records: HashMap<String, BTreeMap<String, FieldHistory>>,
}

impl RecordHistory {
    pub fn new() -> Self {
        RecordHistory {
            records: HashMap::new(),
        }
    }

    pub fn set_value(
        &mut self,
        timestamp: i64,
        record_id: String,
        field: String,
        effective_date: NaiveDate,
        value: String,
    ) {
        self.records
            .entry(record_id)
            .or_default()
            .entry(field)
            .or_default()
            .write(timestamp, effective_date, value);
    }

    pub fn get_value(
        &mut self,
        _timestamp: i64,
        record_id: String,
        field: String,
        on_date: NaiveDate,
    ) -> String {
        self.history(&record_id, &field)
            .map(|history| history.current(on_date))
            .unwrap_or_default()
    }

    pub fn snapshot(
        &mut self,
        _timestamp: i64,
        record_id: String,
        on_date: NaiveDate,
    ) -> Vec<String> {
        self.snapshot_with(&record_id, |history| history.current(on_date))
    }

    pub fn get_value_as_known(
        &mut self,
        _timestamp: i64,
        record_id: String,
        field: String,
        on_date: NaiveDate,
        known_at: i64,
    ) -> String {
        self.history(&record_id, &field)
            .map(|history| history.as_known(on_date, known_at))
            .unwrap_or_default()
    }

    pub fn snapshot_as_known(
        &mut self,
        _timestamp: i64,
        record_id: String,
        on_date: NaiveDate,
        known_at: i64,
    ) -> Vec<String> {
        self.snapshot_with(&record_id, |history| history.as_known(on_date, known_at))
    }

    fn history(&self, record_id: &str, field: &str) -> Option<&FieldHistory> {
        self.records.get(record_id)?.get(field)
    }

    fn snapshot_with(
        &self,
        record_id: &str,
        read: impl Fn(&FieldHistory) -> String,
    ) -> Vec<String> {
        let Some(fields) = self.records.get(record_id) else {
            return vec![];
        };
        fields
            .iter()
            .filter_map(|(name, history)| {
                let value = read(history);
                (!value.is_empty()).then(|| format!("{name}={value}"))
            })
            .collect()
    }
}
