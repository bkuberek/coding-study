use chrono::NaiveDate;
use rust_decimal::{Decimal, RoundingStrategy};

const CENTS: u32 = 2;

pub fn unearned_premium(
    term_premium: Decimal,
    term_start: NaiveDate,
    term_end: NaiveDate,
    change_date: NaiveDate,
) -> Decimal {
    if change_date < term_start || change_date > term_end {
        return Decimal::NEGATIVE_ONE;
    }
    let remaining = (term_end - change_date).num_days();
    let term_days = (term_end - term_start).num_days();
    // `/` keeps 28 significant digits, so rounding its result to cents is the exact answer: a
    // quotient by a count of days never ends in a run of 9s. `MidpointAwayFromZero` is `HALF_UP`.
    (term_premium * Decimal::from(remaining) / Decimal::from(term_days))
        .round_dp_with_strategy(CENTS, RoundingStrategy::MidpointAwayFromZero)
}
