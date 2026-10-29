//! A small JSON reader and writer, so the runner needs no crates (docs/decisions/0012-go-and-rust.md).
//!
//! Numbers are kept as `Int` when their text is an integer that fits `i64`, which every DSL
//! `int` and `long` does, and as `Float` otherwise. Neither allocates, so a bench input of a
//! million numbers stays compact.

use std::fmt::Write as _;

/// Requests nest values far less deeply; the limit only keeps a malformed file from overflowing
/// the stack.
const MAX_DEPTH: usize = 1000;

#[derive(Clone, Debug, PartialEq)]
pub enum Json {
    Null,
    Bool(bool),
    Int(i64),
    Float(f64),
    String(String),
    Array(Vec<Json>),
    /// Fields in document order.
    Object(Vec<(String, Json)>),
}

impl Json {
    pub fn parse(text: &str) -> Result<Json, String> {
        let mut parser = Parser {
            text,
            bytes: text.as_bytes(),
            pos: 0,
        };
        parser.skip_whitespace();
        let value = parser.value(0)?;
        parser.skip_whitespace();
        if parser.pos != parser.bytes.len() {
            return Err(parser.error("trailing characters"));
        }
        Ok(value)
    }

    pub fn get(&self, key: &str) -> Option<&Json> {
        match self {
            Json::Object(fields) => fields
                .iter()
                .find(|(name, _)| name == key)
                .map(|(_, value)| value),
            _ => None,
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            Json::String(text) => Some(text),
            _ => None,
        }
    }

    pub fn as_array(&self) -> Option<&[Json]> {
        match self {
            Json::Array(items) => Some(items),
            _ => None,
        }
    }

    pub fn as_i64(&self) -> Option<i64> {
        match self {
            Json::Int(value) => Some(*value),
            _ => None,
        }
    }

    pub fn as_f64(&self) -> Option<f64> {
        match self {
            Json::Int(value) => Some(*value as f64),
            Json::Float(value) => Some(*value),
            _ => None,
        }
    }

    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Json::Bool(value) => Some(*value),
            _ => None,
        }
    }

    /// The value as compact JSON text.
    pub fn text(&self) -> String {
        let mut out = String::new();
        self.write_to(&mut out);
        out
    }

    pub fn write_to(&self, out: &mut String) {
        match self {
            Json::Null => out.push_str("null"),
            Json::Bool(value) => out.push_str(if *value { "true" } else { "false" }),
            Json::Int(value) => {
                let _ = write!(out, "{value}");
            }
            Json::Float(value) => write_float(*value, out),
            Json::String(text) => write_string(text, out),
            Json::Array(items) => {
                out.push('[');
                for (index, item) in items.iter().enumerate() {
                    if index > 0 {
                        out.push(',');
                    }
                    item.write_to(out);
                }
                out.push(']');
            }
            Json::Object(fields) => {
                out.push('{');
                for (index, (name, value)) in fields.iter().enumerate() {
                    if index > 0 {
                        out.push(',');
                    }
                    write_string(name, out);
                    out.push(':');
                    value.write_to(out);
                }
                out.push('}');
            }
        }
    }
}

/// `{:?}` is the shortest text that reads back as the same double, and it always shows the type:
/// `3.0`, `0.1`, `1e-9`, `1.7976931348623157e308`. Encoders reject non-finite values first;
/// this writes `null` for them so the event line stays valid JSON.
fn write_float(value: f64, out: &mut String) {
    if value.is_finite() {
        let _ = write!(out, "{value:?}");
    } else {
        out.push_str("null");
    }
}

fn write_string(text: &str, out: &mut String) {
    out.push('"');
    for c in text.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => {
                let _ = write!(out, "\\u{:04x}", c as u32);
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

struct Parser<'a> {
    text: &'a str,
    bytes: &'a [u8],
    pos: usize,
}

impl Parser<'_> {
    fn error(&self, what: &str) -> String {
        format!("invalid JSON at byte {}: {what}", self.pos)
    }

    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.pos).copied()
    }

    fn eat(&mut self, byte: u8) -> bool {
        let found = self.peek() == Some(byte);
        if found {
            self.pos += 1;
        }
        found
    }

    fn skip_whitespace(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\n' | b'\r' | b'\t')) {
            self.pos += 1;
        }
    }

    fn value(&mut self, depth: usize) -> Result<Json, String> {
        if depth > MAX_DEPTH {
            return Err(self.error("nested too deeply"));
        }
        match self.peek() {
            Some(b'n') => self.literal("null", Json::Null),
            Some(b't') => self.literal("true", Json::Bool(true)),
            Some(b'f') => self.literal("false", Json::Bool(false)),
            Some(b'"') => self.string().map(Json::String),
            Some(b'[') => self.array(depth),
            Some(b'{') => self.object(depth),
            Some(b'-' | b'0'..=b'9') => self.number(),
            _ => Err(self.error("expected a value")),
        }
    }

    fn literal(&mut self, word: &str, value: Json) -> Result<Json, String> {
        if !self.bytes[self.pos..].starts_with(word.as_bytes()) {
            return Err(self.error("unknown literal"));
        }
        self.pos += word.len();
        Ok(value)
    }

    fn digits(&mut self) -> Result<(), String> {
        if !matches!(self.peek(), Some(b'0'..=b'9')) {
            return Err(self.error("expected a digit"));
        }
        while matches!(self.peek(), Some(b'0'..=b'9')) {
            self.pos += 1;
        }
        Ok(())
    }

    fn number(&mut self) -> Result<Json, String> {
        let start = self.pos;
        self.eat(b'-');
        if !self.eat(b'0') {
            self.digits()?;
        }
        let mut integral = true;
        if self.eat(b'.') {
            integral = false;
            self.digits()?;
        }
        if self.eat(b'e') || self.eat(b'E') {
            integral = false;
            let _ = self.eat(b'+') || self.eat(b'-');
            self.digits()?;
        }
        let text = &self.text[start..self.pos];
        if integral {
            if let Ok(value) = text.parse::<i64>() {
                return Ok(Json::Int(value));
            }
        }
        text.parse::<f64>()
            .map(Json::Float)
            .map_err(|_| self.error("bad number"))
    }

    fn string(&mut self) -> Result<String, String> {
        self.pos += 1;
        let mut out = String::new();
        loop {
            let start = self.pos;
            // Stops only at ASCII bytes, so both ends are char boundaries.
            while matches!(self.peek(), Some(byte) if byte != b'"' && byte != b'\\' && byte >= 0x20)
            {
                self.pos += 1;
            }
            out.push_str(&self.text[start..self.pos]);
            match self.peek() {
                Some(b'"') => {
                    self.pos += 1;
                    return Ok(out);
                }
                Some(b'\\') => {
                    self.pos += 1;
                    self.escape(&mut out)?;
                }
                _ => return Err(self.error("unterminated string")),
            }
        }
    }

    fn escape(&mut self, out: &mut String) -> Result<(), String> {
        let byte = self
            .peek()
            .ok_or_else(|| self.error("unterminated escape"))?;
        self.pos += 1;
        match byte {
            b'"' => out.push('"'),
            b'\\' => out.push('\\'),
            b'/' => out.push('/'),
            b'b' => out.push('\u{8}'),
            b'f' => out.push('\u{c}'),
            b'n' => out.push('\n'),
            b'r' => out.push('\r'),
            b't' => out.push('\t'),
            b'u' => {
                let first = self.hex4()?;
                let code = if (0xD800..0xDC00).contains(&first) {
                    if !(self.eat(b'\\') && self.eat(b'u')) {
                        return Err(self.error("lone surrogate"));
                    }
                    let second = self.hex4()?;
                    if !(0xDC00..0xE000).contains(&second) {
                        return Err(self.error("invalid surrogate pair"));
                    }
                    0x10000 + ((first - 0xD800) << 10) + (second - 0xDC00)
                } else {
                    first
                };
                out.push(char::from_u32(code).ok_or_else(|| self.error("invalid code point"))?);
            }
            _ => return Err(self.error("unknown escape")),
        }
        Ok(())
    }

    fn hex4(&mut self) -> Result<u32, String> {
        let digits = self.text.get(self.pos..self.pos + 4).unwrap_or("");
        if digits.len() != 4 || !digits.bytes().all(|byte| byte.is_ascii_hexdigit()) {
            return Err(self.error("bad \\u escape"));
        }
        self.pos += 4;
        u32::from_str_radix(digits, 16).map_err(|_| self.error("bad \\u escape"))
    }

    fn array(&mut self, depth: usize) -> Result<Json, String> {
        self.pos += 1;
        let mut items = Vec::new();
        self.skip_whitespace();
        if self.eat(b']') {
            return Ok(Json::Array(items));
        }
        loop {
            self.skip_whitespace();
            items.push(self.value(depth + 1)?);
            self.skip_whitespace();
            if self.eat(b']') {
                return Ok(Json::Array(items));
            }
            if !self.eat(b',') {
                return Err(self.error("expected ',' or ']'"));
            }
        }
    }

    fn object(&mut self, depth: usize) -> Result<Json, String> {
        self.pos += 1;
        let mut fields = Vec::new();
        self.skip_whitespace();
        if self.eat(b'}') {
            return Ok(Json::Object(fields));
        }
        loop {
            self.skip_whitespace();
            if self.peek() != Some(b'"') {
                return Err(self.error("expected a field name"));
            }
            let name = self.string()?;
            self.skip_whitespace();
            if !self.eat(b':') {
                return Err(self.error("expected ':'"));
            }
            self.skip_whitespace();
            fields.push((name, self.value(depth + 1)?));
            self.skip_whitespace();
            if self.eat(b'}') {
                return Ok(Json::Object(fields));
            }
            if !self.eat(b',') {
                return Err(self.error("expected ',' or '}'"));
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::Json;

    fn round_trip(text: &str) -> String {
        Json::parse(text).unwrap().text()
    }

    #[test]
    fn keeps_integers_exact_and_unicode_intact() {
        assert_eq!(
            round_trip(r#"{"a": [1, -0, 9007199254740991], "b": "\u00fc\ud83d\ude00 \"q\" \n"}"#),
            "{\"a\":[1,0,9007199254740991],\"b\":\"ü😀 \\\"q\\\" \\n\"}"
        );
    }

    #[test]
    fn reads_fractions_and_exponents_as_floats() {
        assert_eq!(Json::parse("-2.5e3"), Ok(Json::Float(-2500.0)));
        assert_eq!(Json::parse("3.0"), Ok(Json::Float(3.0)));
        assert_eq!(Json::parse("1e2"), Ok(Json::Float(100.0)));
    }

    #[test]
    fn an_integer_beyond_i64_is_a_float() {
        assert_eq!(
            Json::parse("92233720368547758070"),
            Ok(Json::Float(92233720368547758070.0))
        );
    }

    #[test]
    fn writes_floats_as_doubles() {
        let values = Json::Array(vec![
            Json::Float(3.0),
            Json::Float(0.1),
            Json::Float(1e-9),
            Json::Float(f64::MAX),
            Json::Float(f64::NAN),
        ]);
        assert_eq!(values.text(), "[3.0,0.1,1e-9,1.7976931348623157e308,null]");
    }

    #[test]
    fn escapes_control_characters() {
        assert_eq!(
            Json::String("a\u{1}b\tc".into()).text(),
            "\"a\\u0001b\\tc\""
        );
    }

    #[test]
    fn rejects_bad_input() {
        for bad in [
            "",
            "[1,]",
            "01",
            "\"\\ud800\"",
            "{\"a\" 1}",
            "[1] x",
            "-",
            "1.",
            "\"\\u+123\"",
            "\"open",
            "nul",
        ] {
            assert!(Json::parse(bad).is_err(), "{bad} should not parse");
        }
    }

    #[test]
    fn rejects_deep_nesting() {
        let deep = format!("{}{}", "[".repeat(2000), "]".repeat(2000));
        assert!(Json::parse(&deep).is_err());
    }
}
