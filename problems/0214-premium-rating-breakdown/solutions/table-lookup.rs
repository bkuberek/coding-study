use std::collections::HashMap;

use rust_decimal::{Decimal, RoundingStrategy};

const CENTS: u32 = 2;

// The stub fixes the nine parameters.
#[allow(clippy::too_many_arguments)]
pub fn rate_premium(
    class_code: String,
    payroll: Decimal,
    experience_mod: Decimal,
    schedule_credit: Decimal,
    class_codes: Vec<String>,
    base_rates: Vec<Decimal>,
    band_lower_bounds: Vec<Decimal>,
    band_factors: Vec<Decimal>,
    minimum_premium: Decimal,
) -> Vec<Decimal> {
    let rates: HashMap<String, Decimal> = class_codes.into_iter().zip(base_rates).collect();
    // Bands whose lower bound is <= payroll (upper bound of the sorted bounds).
    let bands_at_or_below = band_lower_bounds.partition_point(|bound| *bound <= payroll);
    let Some(&rate) = rates.get(&class_code) else {
        return vec![];
    };
    if bands_at_or_below == 0 {
        return vec![];
    }
    // Multiplying by 0.001 only moves the decimal point, so dividing by 1000 stays exact.
    let mut running = payroll * Decimal::new(1, 3) * rate;
    let mut trail = vec![running];
    let factors = [
        band_factors[bands_at_or_below - 1],
        experience_mod,
        Decimal::ONE - schedule_credit,
    ];
    for factor in factors {
        running *= factor;
        trail.push(running);
    }
    // `MidpointAwayFromZero` is Java's `HALF_UP`.
    trail.push(
        running
            .max(minimum_premium)
            .round_dp_with_strategy(CENTS, RoundingStrategy::MidpointAwayFromZero),
    );
    trail
}
