use chrono::{Datelike, NaiveDate};
use rust_decimal::{Decimal, RoundingStrategy};

const RATIO_PLACES: u32 = 4;

pub fn loss_ratios(
    earned_dates: Vec<NaiveDate>,
    earned_amounts: Vec<Decimal>,
    loss_dates: Vec<NaiveDate>,
    loss_amounts: Vec<Decimal>,
    from_date: NaiveDate,
    to_date: NaiveDate,
    period_months: i32,
) -> Vec<Decimal> {
    let first = period_index(from_date, period_months);
    let count = period_index(to_date, period_months) - first + 1;
    let earned = sum_by_period(&earned_dates, &earned_amounts, period_months, first, count);
    let losses = sum_by_period(&loss_dates, &loss_amounts, period_months, first, count);
    earned
        .iter()
        .zip(&losses)
        .map(|(&earned, &loss)| {
            // `is_zero` tests the value: a total of 0.00 is zero, and dividing by it would panic.
            if earned.is_zero() {
                Decimal::NEGATIVE_ONE
            } else {
                // `/` keeps 28 significant digits. With sums of at most 10^9 and two fractional
                // digits, a quotient that is not exactly a tie stays more than 10^-16 away from
                // it, so the rounding that follows is exact. `MidpointAwayFromZero` is Java's
                // `HALF_UP`.
                (loss / earned)
                    .round_dp_with_strategy(RATIO_PLACES, RoundingStrategy::MidpointAwayFromZero)
            }
        })
        .collect()
}

/// Periods are calendar-aligned blocks of months counted from January of year 0.
fn period_index(day: NaiveDate, period_months: i32) -> i32 {
    (day.year() * 12 + day.month() as i32 - 1) / period_months
}

fn sum_by_period(
    dates: &[NaiveDate],
    amounts: &[Decimal],
    period_months: i32,
    first: i32,
    count: i32,
) -> Vec<Decimal> {
    let mut totals = vec![Decimal::ZERO; count as usize];
    for (&day, &amount) in dates.iter().zip(amounts) {
        let slot = period_index(day, period_months) - first;
        if (0..count).contains(&slot) {
            totals[slot as usize] += amount;
        }
    }
    totals
}
