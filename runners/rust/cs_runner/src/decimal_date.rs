//! `decimal` and `date` (docs/specs/problem-format.md#decimal-and-date): `rust_decimal::Decimal`
//! and `chrono::NaiveDate`, vendored. Both travel as JSON strings. A decimal input keeps its
//! scale, and an output is written canonically, without trailing fractional zeros or `-0`, so
//! equal numbers have equal text.

use chrono::{Datelike, NaiveDate};
use rust_decimal::Decimal;

use crate::codec::{mismatch, Decode, Encode};
use crate::json::Json;

const YEARS: std::ops::RangeInclusive<i32> = 1..=9999;

impl Decode for Decimal {
    /// `from_str_exact` never rounds: a value with more than 28 digits after the point, or of
    /// magnitude 2^96 or more, is an input error rather than a different number.
    fn decode(value: &Json) -> Result<Self, String> {
        let text = value
            .as_str()
            .filter(|text| is_decimal(text))
            .ok_or_else(|| mismatch::<Self>(value))?;
        Decimal::from_str_exact(text).map_err(|_| {
            format!(
                "{} does not fit rust_decimal: at most 28 digits after the point and a \
                 magnitude below 2^96",
                value.text()
            )
        })
    }

    fn name() -> String {
        "decimal".into()
    }
}

impl Encode for Decimal {
    /// `normalize` strips the trailing zeros and turns `-0` into `0`; `Display` never writes an
    /// exponent.
    fn encode(&self) -> Result<Json, String> {
        Ok(Json::String(self.normalize().to_string()))
    }
}

impl Decode for NaiveDate {
    fn decode(value: &Json) -> Result<Self, String> {
        let text = value
            .as_str()
            .filter(|text| is_iso_date(text))
            .ok_or_else(|| mismatch::<Self>(value))?;
        let field = |range: std::ops::Range<usize>| text[range].parse::<u32>().unwrap_or(0);
        let year = i32::try_from(field(0..4)).unwrap_or(0);
        NaiveDate::from_ymd_opt(year, field(5..7), field(8..10))
            .filter(|day| YEARS.contains(&day.year()))
            .ok_or_else(|| format!("{} is not a calendar day", value.text()))
    }

    fn name() -> String {
        "date".into()
    }
}

impl Encode for NaiveDate {
    fn encode(&self) -> Result<Json, String> {
        if !YEARS.contains(&self.year()) {
            return Err(format!("date out of range: {self}"));
        }
        let text = format!("{:04}-{:02}-{:02}", self.year(), self.month(), self.day());
        Ok(Json::String(text))
    }
}

/// `^-?(0|[1-9][0-9]*)(\.[0-9]+)?$`
fn is_decimal(text: &str) -> bool {
    let digits = |part: &str| !part.is_empty() && part.bytes().all(|b| b.is_ascii_digit());
    let unsigned = text.strip_prefix('-').unwrap_or(text);
    let (whole, fraction) = match unsigned.split_once('.') {
        Some((whole, fraction)) => (whole, Some(fraction)),
        None => (unsigned, None),
    };
    digits(whole) && (whole == "0" || !whole.starts_with('0')) && fraction.into_iter().all(digits)
}

/// `^[0-9]{4}-[0-9]{2}-[0-9]{2}$`
fn is_iso_date(text: &str) -> bool {
    text.len() == 10
        && text.bytes().enumerate().all(|(index, byte)| match index {
            4 | 7 => byte == b'-',
            _ => byte.is_ascii_digit(),
        })
}

#[cfg(test)]
mod tests {
    use chrono::NaiveDate;
    use rust_decimal::Decimal;

    use crate::codec::{Decode, Encode};
    use crate::json::Json;

    fn parsed(text: &str) -> Json {
        Json::parse(text).unwrap()
    }

    fn round_trip<T: Decode + Encode>(text: &str) -> String {
        T::decode(&parsed(text)).unwrap().encode().unwrap().text()
    }

    #[test]
    fn decimals_come_back_canonical() {
        for (input, output) in [
            ("\"2500.00\"", "\"2500\""),
            ("\"-0.0\"", "\"0\""),
            ("\"-12.340\"", "\"-12.34\""),
            ("\"100\"", "\"100\""),
            (
                "\"-9999999999999999999999999999\"",
                "\"-9999999999999999999999999999\"",
            ),
            (
                "\"0.0000000000000000000000000001\"",
                "\"0.0000000000000000000000000001\"",
            ),
        ] {
            assert_eq!(round_trip::<Decimal>(input), output, "{input}");
        }
    }

    #[test]
    fn decimal_inputs_keep_their_scale() {
        assert_eq!(
            Decimal::decode(&parsed("\"2500.00\"")).map(|d| d.scale()),
            Ok(2)
        );
    }

    #[test]
    fn equal_decimals_encode_equally() {
        let one_and_a_half = Decimal::new(150, 2).encode();
        assert_eq!(one_and_a_half, Decimal::new(15, 1).encode());
        let negative_zero = -Decimal::new(0, 3);
        assert!(negative_zero.is_sign_negative());
        assert_eq!(negative_zero.encode(), Ok(Json::String("0".into())));
    }

    #[test]
    fn malformed_decimals_are_invalid_input() {
        for (input, message) in [
            ("1.5", "expected decimal, got 1.5"),
            ("\"1e5\"", "expected decimal, got \"1e5\""),
            ("\"01.5\"", "expected decimal, got \"01.5\""),
            ("\"1.\"", "expected decimal, got \"1.\""),
            ("\"+1\"", "expected decimal, got \"+1\""),
            ("\"-\"", "expected decimal, got \"-\""),
        ] {
            assert_eq!(
                Decimal::decode(&parsed(input)),
                Err(message.into()),
                "{input}"
            );
        }
    }

    #[test]
    fn decimals_beyond_rust_decimal_are_invalid_input() {
        let message = "\"0.00000000000000000000000000001\" does not fit rust_decimal: at most 28 \
                       digits after the point and a magnitude below 2^96";
        assert_eq!(
            Decimal::decode(&parsed("\"0.00000000000000000000000000001\"")),
            Err(message.into())
        );
        assert!(Decimal::decode(&parsed("\"100000000000000000000000000000\"")).is_err());
    }

    #[test]
    fn dates_round_trip() {
        for text in ["\"2024-02-29\"", "\"0001-01-01\"", "\"9999-12-31\""] {
            assert_eq!(round_trip::<NaiveDate>(text), text);
        }
        let matrix = "[[\"2024-01-01\"],[]]";
        assert_eq!(round_trip::<Vec<Vec<NaiveDate>>>(matrix), matrix);
    }

    #[test]
    fn malformed_dates_and_unreal_days_are_invalid_input() {
        for (input, message) in [
            ("\"2024-1-01\"", "expected date, got \"2024-1-01\""),
            ("20240101", "expected date, got 20240101"),
            (
                "\"2024-01-01T00:00\"",
                "expected date, got \"2024-01-01T00:00\"",
            ),
            ("\"2023-02-29\"", "\"2023-02-29\" is not a calendar day"),
            ("\"0000-01-01\"", "\"0000-01-01\" is not a calendar day"),
        ] {
            assert_eq!(
                NaiveDate::decode(&parsed(input)),
                Err(message.into()),
                "{input}"
            );
        }
    }

    #[test]
    fn dates_outside_years_1_to_9999_are_invalid_output() {
        let late = NaiveDate::from_ymd_opt(10000, 1, 1).unwrap();
        assert_eq!(late.encode(), Err("date out of range: +10000-01-01".into()));
        let early = NaiveDate::from_ymd_opt(0, 12, 31).unwrap();
        assert_eq!(early.encode(), Err("date out of range: 0000-12-31".into()));
    }
}
