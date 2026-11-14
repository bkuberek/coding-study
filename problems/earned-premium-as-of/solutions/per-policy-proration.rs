use chrono::NaiveDate;
use rust_decimal::{Decimal, RoundingStrategy};

const CENTS: u32 = 2;

pub fn earned_premium(
    premiums: Vec<Decimal>,
    terms: Vec<Vec<NaiveDate>>,
    valuation_date: NaiveDate,
) -> Decimal {
    let mut total = Decimal::ZERO;
    for (premium, term) in premiums.iter().zip(&terms) {
        let term_days = (term[1] - term[0]).num_days();
        let earned_days = (valuation_date - term[0]).num_days().clamp(0, term_days);
        // Each policy is rounded to cents on its own; the book total is the sum of rounded
        // amounts. `/` keeps 28 significant digits, so the rounding that follows is exact: a
        // quotient by a count of days never ends in a run of 9s. `MidpointAwayFromZero` is
        // Java's `HALF_UP`.
        total += (premium * Decimal::from(earned_days) / Decimal::from(term_days))
            .round_dp_with_strategy(CENTS, RoundingStrategy::MidpointAwayFromZero);
    }
    total
}
