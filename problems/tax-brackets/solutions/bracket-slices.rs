use rust_decimal::Decimal;

pub fn calculate_tax(brackets: Vec<Vec<i32>>, income: i32) -> Decimal {
    let mut cents: i64 = 0; // tax in hundredths of a unit: every rate is a whole percent
    let mut lower = 0;
    for bracket in &brackets {
        if lower >= income {
            break;
        }
        cents += i64::from((bracket[0].min(income) - lower) * bracket[1]);
        lower = bracket[0];
    }
    // Built once, from the integer count of hundredths: no division, no rounding.
    Decimal::new(cents, 2)
}
