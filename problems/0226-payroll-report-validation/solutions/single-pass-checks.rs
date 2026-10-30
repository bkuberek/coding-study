use std::cmp::Ordering;
use std::collections::HashSet;

use chrono::{Datelike, NaiveDate};

const FIELDS: [&str; 4] = ["contractorId", "classCode", "payroll", "periodStart"];
const MAX_PAYROLL: &str = "1000000000";
const FIRST_YEAR: i32 = 2000;
const LAST_YEAR: i32 = 2099;

pub fn validate_rows(rows: Vec<Vec<String>>) -> Vec<String> {
    let mut errors = Vec::new();
    let mut seen_keys: HashSet<(&str, &str, &str)> = HashSet::new();
    for (index, row) in rows.iter().enumerate() {
        let [contractor_id, class_code, payroll, period_start] = row.as_slice() else {
            errors.push(format!("{index}:row:column-count"));
            continue;
        };
        let reasons = [
            check_pattern(contractor_id, is_contractor_id),
            check_pattern(class_code, is_class_code),
            check_payroll(payroll),
            check_period_start(period_start),
        ];
        for (field, reason) in FIELDS.iter().zip(reasons) {
            if !reason.is_empty() {
                errors.push(format!("{index}:{field}:{reason}"));
            }
        }
        if reasons[0].is_empty() && reasons[1].is_empty() && reasons[3].is_empty() {
            let key = (
                contractor_id.as_str(),
                class_code.as_str(),
                period_start.as_str(),
            );
            if !seen_keys.insert(key) {
                errors.push(format!("{index}:row:duplicate"));
            }
        }
    }
    errors
}

fn check_pattern(value: &str, has_shape: fn(&str) -> bool) -> &'static str {
    if value.is_empty() {
        "missing"
    } else if has_shape(value) {
        ""
    } else {
        "invalid"
    }
}

/// 1 to 20 of `[a-z0-9-]`.
fn is_contractor_id(value: &str) -> bool {
    (1..=20).contains(&value.len())
        && value
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
}

/// Exactly four digits.
fn is_class_code(value: &str) -> bool {
    value.len() == 4 && value.bytes().all(|byte| byte.is_ascii_digit())
}

/// Digits, then optionally a point and one or two digits.
fn is_payroll(value: &str) -> bool {
    let (whole, fraction) = value.split_once('.').unwrap_or((value, "0"));
    !whole.is_empty()
        && whole.bytes().all(|byte| byte.is_ascii_digit())
        && (1..=2).contains(&fraction.len())
        && fraction.bytes().all(|byte| byte.is_ascii_digit())
}

/// `YYYY-MM-DD` with ASCII digits only.
fn is_iso_day(value: &str) -> bool {
    value.len() == 10
        && value
            .bytes()
            .enumerate()
            .all(|(position, byte)| match position {
                4 | 7 => byte == b'-',
                _ => byte.is_ascii_digit(),
            })
}

fn check_payroll(value: &str) -> &'static str {
    let reason = check_pattern(value, is_payroll);
    if !reason.is_empty() {
        return reason;
    }
    // The amount is compared on its digits: `rust_decimal` holds 28 digits, and a value may have 40.
    let (whole, fraction) = value.split_once('.').unwrap_or((value, ""));
    let whole = whole.trim_start_matches('0');
    let fraction_is_zero = fraction.bytes().all(|byte| byte == b'0');
    let positive = !whole.is_empty() || !fraction_is_zero;
    let within_max = match whole.len().cmp(&MAX_PAYROLL.len()) {
        Ordering::Less => true,
        Ordering::Greater => false,
        Ordering::Equal => match whole.cmp(MAX_PAYROLL) {
            Ordering::Less => true,
            Ordering::Equal => fraction_is_zero,
            Ordering::Greater => false,
        },
    };
    if positive && within_max {
        ""
    } else {
        "out-of-range"
    }
}

fn check_period_start(value: &str) -> &'static str {
    let reason = check_pattern(value, is_iso_day);
    if !reason.is_empty() {
        return reason;
    }
    let number = |range: std::ops::Range<usize>| value[range].parse::<u32>().unwrap_or(0);
    let (year, month, day) = (number(0..4), number(5..7), number(8..10));
    // `from_ymd_opt` rejects 30 February; year 0 exists for chrono but not for this problem.
    match NaiveDate::from_ymd_opt(year as i32, month, day) {
        Some(date) if year >= 1 => {
            if (FIRST_YEAR..=LAST_YEAR).contains(&date.year()) {
                ""
            } else {
                "out-of-range"
            }
        }
        _ => "invalid",
    }
}
