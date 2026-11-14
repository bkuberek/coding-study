use rust_decimal::Decimal;

pub fn calculate_tax(brackets: Vec<Vec<i32>>, income: i32) -> Decimal {
    let mut cents: i64 = 0; // tax in hundredths of a unit: every rate is a whole percent
    let mut bracket = 0;
    for unit in 0..income {
        // Unit number `unit` covers income from `unit` to `unit + 1`.
        while brackets[bracket][0] <= unit {
            bracket += 1;
        }
        cents += i64::from(brackets[bracket][1]);
    }
    // Built once, from the integer count of hundredths: no division, no rounding.
    Decimal::new(cents, 2)
}
