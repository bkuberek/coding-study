use chrono::{Months, NaiveDate};
use rust_decimal::prelude::ToPrimitive;
use rust_decimal::Decimal;

const CENTS: u32 = 2;

pub fn installment_schedule(
    premium: Decimal,
    installment_count: i32,
    first_due_date: NaiveDate,
) -> Vec<Vec<String>> {
    if installment_count == 0 {
        return vec![];
    }
    // Exact: at most two fractional digits, so the product is a whole number of cents.
    let total_cents = (premium * Decimal::ONE_HUNDRED)
        .to_i64()
        .expect("premium in cents fits in an i64");
    let count = i64::from(installment_count);
    let base = total_cents / count;
    let leftover = total_cents % count;
    (0..count)
        .map(|number| {
            // Leftover cents go to the first installments.
            let amount = if number < leftover { base + 1 } else { base };
            // `checked_add_months` counts from the anchor and clamps to the last day of a short
            // month, like Java's `plusMonths`.
            let due = first_due_date
                .checked_add_months(Months::new(number as u32))
                .expect("due date within the supported years");
            vec![due.to_string(), Decimal::new(amount, CENTS).to_string()]
        })
        .collect()
}
