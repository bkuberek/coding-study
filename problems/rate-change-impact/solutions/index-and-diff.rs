use std::collections::HashMap;

use rust_decimal::{Decimal, RoundingStrategy};

const PERCENT_PLACES: u32 = 2;

pub fn rate_change_impact(
    old_codes: Vec<String>,
    old_rates: Vec<Decimal>,
    new_codes: Vec<String>,
    new_rates: Vec<Decimal>,
) -> Vec<Vec<String>> {
    let old: HashMap<String, Decimal> = old_codes.into_iter().zip(old_rates).collect();
    let current: HashMap<String, Decimal> = new_codes.into_iter().zip(new_rates).collect();

    let mut changed: Vec<(Decimal, &str)> = Vec::new();
    let mut added: Vec<&str> = Vec::new();
    for (code, &rate) in &current {
        match old.get(code) {
            None => added.push(code),
            // `!=` compares by value: 12.50 equals 12.5.
            Some(&before) if rate != before => {
                // `/` keeps 28 significant digits. With rates of at most 10^4 and four fractional
                // digits, a quotient that is not exactly a tie stays far away from it, so the
                // rounding that follows is exact. `MidpointAwayFromZero` is Java's `HALF_UP`.
                let percent = ((rate - before) * Decimal::ONE_HUNDRED / before)
                    .round_dp_with_strategy(PERCENT_PLACES, RoundingStrategy::MidpointAwayFromZero);
                changed.push((percent, code));
            }
            Some(_) => {}
        }
    }
    let mut removed: Vec<&str> = old
        .keys()
        .filter(|code| !current.contains_key(*code))
        .map(String::as_str)
        .collect();

    // Numeric order of the rounded percent, largest first; ties by code in byte order.
    changed.sort_by(|a, b| b.0.cmp(&a.0).then_with(|| a.1.cmp(b.1)));
    added.sort();
    removed.sort();

    let mut rows: Vec<Vec<String>> = Vec::new();
    for (percent, code) in changed {
        rows.push(vec![
            code.to_string(),
            "changed".to_string(),
            percent_text(percent),
        ]);
    }
    for code in added {
        rows.push(vec![code.to_string(), "added".to_string(), String::new()]);
    }
    for code in removed {
        rows.push(vec![code.to_string(), "removed".to_string(), String::new()]);
    }
    rows
}

/// Writes the percent with exactly two fractional digits, and `0.00` for a zero that kept a
/// minus sign.
fn percent_text(percent: Decimal) -> String {
    let mut text = if percent.is_zero() {
        Decimal::ZERO
    } else {
        percent
    };
    text.rescale(PERCENT_PLACES);
    text.to_string()
}
