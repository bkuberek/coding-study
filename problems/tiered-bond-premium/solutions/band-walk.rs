use rust_decimal::{Decimal, RoundingStrategy};

const CENTS: u32 = 2;

pub fn bond_premium(
    contract_price: Decimal,
    band_floors: Vec<Decimal>,
    rates_per_thousand: Vec<Decimal>,
) -> Decimal {
    let mut total = Decimal::ZERO; // sum of slice * rate, exact
    for (band, &lower) in band_floors.iter().enumerate() {
        if contract_price <= lower {
            break;
        }
        let upper = band_floors.get(band + 1).copied().unwrap_or(contract_price);
        let slice = contract_price.min(upper) - lower;
        total += slice * rates_per_thousand[band];
    }
    // Multiplying by 0.001 only moves the point, so dividing by 1000 is exact; round once, at the
    // end. `MidpointAwayFromZero` is Java's `HALF_UP`.
    (total * Decimal::new(1, 3))
        .round_dp_with_strategy(CENTS, RoundingStrategy::MidpointAwayFromZero)
}
