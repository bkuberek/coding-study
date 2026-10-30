use std::collections::HashMap;

use chrono::NaiveDate;
use rust_decimal::Decimal;

struct Version {
    id: i32,
    rates: HashMap<String, Decimal>,
}

pub struct RateTable {
    /// Parallel vectors sorted by effective date; equal dates stay in publish order.
    dates: Vec<NaiveDate>,
    versions: Vec<Version>,
    published: i32,
}

impl RateTable {
    pub fn new() -> Self {
        RateTable {
            dates: Vec::new(),
            versions: Vec::new(),
            published: 0,
        }
    }

    pub fn publish(
        &mut self,
        effective_date: NaiveDate,
        class_codes: Vec<String>,
        rates: Vec<Decimal>,
    ) {
        self.published += 1;
        let slot = self.versions_on_or_before(effective_date);
        // A fresh map, so a published version never changes afterwards.
        let table = class_codes.into_iter().zip(rates).collect();
        self.dates.insert(slot, effective_date);
        self.versions.insert(
            slot,
            Version {
                id: self.published,
                rates: table,
            },
        );
    }

    pub fn rate_as_of(&mut self, on_date: NaiveDate, class_code: String) -> Decimal {
        let slot = self.versions_on_or_before(on_date);
        if slot == 0 {
            return Decimal::NEGATIVE_ONE;
        }
        self.versions[slot - 1]
            .rates
            .get(&class_code)
            .copied()
            .unwrap_or(Decimal::NEGATIVE_ONE)
    }

    pub fn version_as_of(&mut self, on_date: NaiveDate) -> i32 {
        let slot = self.versions_on_or_before(on_date);
        if slot == 0 {
            -1
        } else {
            self.versions[slot - 1].id
        }
    }

    /// The number of versions effective on or before the day (upper bound): `partition_point`
    /// finds the first version after the day, so equal dates fall on the "before" side.
    fn versions_on_or_before(&self, day: NaiveDate) -> usize {
        self.dates.partition_point(|date| *date <= day)
    }
}
