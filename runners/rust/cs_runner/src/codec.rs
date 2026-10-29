//! DSL values to and from Rust types (docs/specs/problem-format.md#go-and-rust-mapping).
//!
//! The generated bridge spells every type, so `Decode` and `Encode` exist only for the types of
//! the mapping table: a solution whose signature uses another type fails to compile in the
//! bridge, which the CLI reports as a `load_error`. Node types are in `nodes`.

use crate::json::Json;

/// `long` values travel as JSON numbers, which TypeScript reads as doubles.
const MAX_SAFE_INTEGER: i64 = (1 << 53) - 1;
const MAX_BMP_CODE_POINT: u32 = 0xFFFF;

/// Builds a fresh value from a case input; the error is the `InvalidInput` message.
pub trait Decode: Sized {
    fn decode(value: &Json) -> Result<Self, String>;

    /// The DSL spelling of the type, for error messages.
    fn name() -> String;
}

/// Serializes a returned value; the error is the `invalid_output` reason.
pub trait Encode {
    fn encode(&self) -> Result<Json, String>;
}

/// `expected int, got "x"`.
pub(crate) fn mismatch<T: Decode>(value: &Json) -> String {
    format!("expected {}, got {}", T::name(), value.text())
}

impl Decode for i32 {
    fn decode(value: &Json) -> Result<Self, String> {
        value
            .as_i64()
            .and_then(|number| i32::try_from(number).ok())
            .ok_or_else(|| mismatch::<Self>(value))
    }

    fn name() -> String {
        "int".into()
    }
}

impl Decode for i64 {
    fn decode(value: &Json) -> Result<Self, String> {
        value.as_i64().ok_or_else(|| mismatch::<Self>(value))
    }

    fn name() -> String {
        "long".into()
    }
}

impl Decode for f64 {
    fn decode(value: &Json) -> Result<Self, String> {
        value.as_f64().ok_or_else(|| mismatch::<Self>(value))
    }

    fn name() -> String {
        "double".into()
    }
}

impl Decode for bool {
    fn decode(value: &Json) -> Result<Self, String> {
        value.as_bool().ok_or_else(|| mismatch::<Self>(value))
    }

    fn name() -> String {
        "bool".into()
    }
}

impl Decode for String {
    fn decode(value: &Json) -> Result<Self, String> {
        value
            .as_str()
            .map(str::to_string)
            .ok_or_else(|| mismatch::<Self>(value))
    }

    fn name() -> String {
        "string".into()
    }
}

impl Decode for char {
    fn decode(value: &Json) -> Result<Self, String> {
        let mut chars = value.as_str().unwrap_or_default().chars();
        match (chars.next(), chars.next()) {
            (Some(c), None) if c as u32 <= MAX_BMP_CODE_POINT => Ok(c),
            _ => Err(mismatch::<Self>(value)),
        }
    }

    fn name() -> String {
        "char".into()
    }
}

impl<T: Decode> Decode for Vec<T> {
    fn decode(value: &Json) -> Result<Self, String> {
        let items = value.as_array().ok_or_else(|| mismatch::<Self>(value))?;
        items.iter().map(T::decode).collect()
    }

    fn name() -> String {
        format!("{}[]", T::name())
    }
}

impl Encode for i32 {
    fn encode(&self) -> Result<Json, String> {
        Ok(Json::Int(i64::from(*self)))
    }
}

impl Encode for i64 {
    fn encode(&self) -> Result<Json, String> {
        if self.abs() > MAX_SAFE_INTEGER {
            return Err(format!("long out of range: {self}"));
        }
        Ok(Json::Int(*self))
    }
}

impl Encode for f64 {
    fn encode(&self) -> Result<Json, String> {
        if !self.is_finite() {
            return Err(format!("non-finite double: {self}"));
        }
        Ok(Json::Float(*self))
    }
}

impl Encode for bool {
    fn encode(&self) -> Result<Json, String> {
        Ok(Json::Bool(*self))
    }
}

impl Encode for String {
    fn encode(&self) -> Result<Json, String> {
        Ok(Json::String(self.clone()))
    }
}

impl Encode for char {
    fn encode(&self) -> Result<Json, String> {
        if *self as u32 > MAX_BMP_CODE_POINT {
            return Err(format!(
                "expected char, got the code point {}",
                *self as u32
            ));
        }
        Ok(Json::String(self.to_string()))
    }
}

impl Encode for () {
    fn encode(&self) -> Result<Json, String> {
        Ok(Json::Null)
    }
}

impl<T: Encode> Encode for Vec<T> {
    /// A failing element names its position: `[2][0]: non-finite double: inf`.
    fn encode(&self) -> Result<Json, String> {
        let mut items = Vec::with_capacity(self.len());
        for (index, item) in self.iter().enumerate() {
            let encoded = item.encode().map_err(|reason| {
                let separator = if reason.starts_with('[') { "" } else { ": " };
                format!("[{index}]{separator}{reason}")
            })?;
            items.push(encoded);
        }
        Ok(Json::Array(items))
    }
}

#[cfg(test)]
mod tests {
    use super::{Decode, Encode};
    use crate::json::Json;

    fn parsed(text: &str) -> Json {
        Json::parse(text).unwrap()
    }

    #[test]
    fn doubles_encode_with_their_type_and_precision() {
        for (value, text) in [(3.0, "3.0"), (1e-9, "1e-9"), (0.1, "0.1"), (-0.5, "-0.5")] {
            assert_eq!(value.encode().map(|json| json.text()), Ok(text.to_string()));
        }
    }

    #[test]
    fn non_finite_doubles_are_invalid_output() {
        assert_eq!(
            f64::INFINITY.encode(),
            Err("non-finite double: inf".to_string())
        );
        assert!(f64::NAN.encode().is_err());
    }

    #[test]
    fn ints_are_range_checked() {
        assert_eq!(
            i32::decode(&parsed("2147483648")),
            Err("expected int, got 2147483648".to_string())
        );
        assert_eq!(i32::decode(&parsed("-2147483648")), Ok(i32::MIN));
        assert_eq!(
            i32::decode(&parsed("3.0")),
            Err("expected int, got 3.0".into())
        );
    }

    #[test]
    fn longs_beyond_two_to_the_53_are_invalid_output() {
        assert_eq!(
            i64::decode(&parsed("9007199254740991")),
            Ok(9007199254740991)
        );
        assert!((1_i64 << 53).encode().is_err());
        assert!((-(1_i64 << 53) + 1).encode().is_ok());
    }

    #[test]
    fn doubles_accept_integer_inputs() {
        assert_eq!(f64::decode(&parsed("2")), Ok(2.0));
    }

    #[test]
    fn chars_are_one_bmp_character() {
        assert_eq!(char::decode(&parsed("\"ü\"")), Ok('ü'));
        assert!(char::decode(&parsed("\"ab\"")).is_err());
        assert!(char::decode(&parsed("\"😀\"")).is_err());
        assert!('😀'.encode().is_err());
    }

    #[test]
    fn nested_vectors_round_trip() {
        let value = parsed("[[1,2],[],[3]]");
        let decoded = Vec::<Vec<i32>>::decode(&value).unwrap();
        assert_eq!(decoded.encode(), Ok(value));
    }

    #[test]
    fn a_mismatch_names_the_dsl_type_and_the_value() {
        assert_eq!(
            Vec::<Vec<String>>::decode(&parsed("[[1]]")),
            Err("expected string, got 1".to_string())
        );
        assert_eq!(
            Vec::<i64>::decode(&parsed("{}")),
            Err("expected long[], got {}".to_string())
        );
    }

    #[test]
    fn an_invalid_element_names_its_position() {
        let value = vec![vec![1.0], vec![2.0, f64::NAN]];
        assert_eq!(value.encode(), Err("[1][1]: non-finite double: NaN".into()));
    }

    #[test]
    fn void_is_null() {
        assert_eq!(().encode(), Ok(Json::Null));
    }
}
