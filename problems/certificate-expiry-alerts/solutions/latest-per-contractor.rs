use std::collections::HashMap;

use chrono::{NaiveDate, TimeDelta};

pub fn certificate_alerts(
    contractor_ids: Vec<String>,
    expiry_dates: Vec<NaiveDate>,
    as_of_date: NaiveDate,
    window_days: i32,
) -> Vec<Vec<String>> {
    // A renewal supersedes: only the latest expiry counts.
    let mut latest: HashMap<String, NaiveDate> = HashMap::new();
    for (id, expiry) in contractor_ids.into_iter().zip(expiry_dates) {
        latest
            .entry(id)
            .and_modify(|current| *current = (*current).max(expiry))
            .or_insert(expiry);
    }
    let horizon = as_of_date + TimeDelta::days(i64::from(window_days));
    // Tuples sort by date, then by id in byte order (the ids are ASCII, so that is code point
    // order).
    let mut flagged: Vec<(NaiveDate, String)> = latest
        .into_iter()
        .filter(|&(_, expiry)| expiry <= horizon)
        .map(|(id, expiry)| (expiry, id))
        .collect();
    flagged.sort();
    flagged
        .into_iter()
        .map(|(expiry, id)| {
            let status = if expiry > as_of_date {
                "expiring"
            } else {
                "expired"
            };
            vec![id, expiry.to_string(), status.to_string()]
        })
        .collect()
}
