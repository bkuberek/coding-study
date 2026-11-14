// Conformance reference: exact decimal arithmetic with explicit rounding, and calendar days.

use chrono::{NaiveDate, TimeDelta};
use rust_decimal::{Decimal, RoundingStrategy};

const CENTS: u32 = 2;

pub struct DecimalDates {}

impl DecimalDates {
    pub fn new() -> Self {
        DecimalDates {}
    }

    pub fn normalized(&mut self, value: Decimal) -> Decimal {
        value
    }

    pub fn add(&mut self, left: Decimal, right: Decimal) -> Decimal {
        left + right
    }

    pub fn total(&mut self, values: Vec<Decimal>) -> Decimal {
        values.iter().sum()
    }

    /// `MidpointAwayFromZero` is Java's `HALF_UP`.
    pub fn round_half_up(&mut self, value: Decimal) -> Decimal {
        value.round_dp_with_strategy(CENTS, RoundingStrategy::MidpointAwayFromZero)
    }

    /// `MidpointNearestEven` is Java's `HALF_EVEN`.
    pub fn round_half_even(&mut self, value: Decimal) -> Decimal {
        value.round_dp_with_strategy(CENTS, RoundingStrategy::MidpointNearestEven)
    }

    /// `/` keeps 28 significant digits; rounding that to cents gives the exact result, because a
    /// quotient by a count of days never ends in a run of 9s.
    pub fn prorate(&mut self, premium: Decimal, days: i32, total_days: i32) -> Decimal {
        (premium * Decimal::from(days) / Decimal::from(total_days))
            .round_dp_with_strategy(CENTS, RoundingStrategy::MidpointAwayFromZero)
    }

    pub fn add_days(&mut self, day: NaiveDate, days: i32) -> NaiveDate {
        day + TimeDelta::days(i64::from(days))
    }

    pub fn days_between(&mut self, start: NaiveDate, end: NaiveDate) -> i32 {
        (end - start).num_days() as i32
    }
}
