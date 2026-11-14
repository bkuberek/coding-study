const CRLF: &str = "\r\n";
const END_OF_HEAD: &str = "\r\n\r\n";
const TOKEN_SYMBOLS: &[u8] = b"!#$%&'*+-.^_`|~";
// A size with more significant digits than this is larger than any limit, so it is never
// converted into a number: that is how a size such as 10000000000000000 (hex) cannot wrap.
const MAX_SIGNIFICANT_DIGITS: usize = 12;
const TOO_MANY_DIGITS: u64 = 1 << 62;

/// Why a stage stopped: it needs more bytes, or the message failed with a code.
enum Stop {
    NeedMore,
    Fail(&'static str),
}

type Rows = Vec<Vec<String>>;

fn row(cells: &[&str]) -> Vec<String> {
    cells.iter().map(|cell| cell.to_string()).collect()
}

fn is_token(text: &str) -> bool {
    !text.is_empty() && text.bytes().all(|c| c.is_ascii_alphanumeric() || TOKEN_SYMBOLS.contains(&c))
}

fn trim_ows(text: &str) -> &str {
    text.trim_matches(|c| c == ' ' || c == '\t')
}

/// The value of a run of digits, or a huge number when it has too many digits to matter.
fn size_of(digits: &str, radix: u32) -> u64 {
    let significant = digits.trim_start_matches('0');
    if significant.is_empty() {
        0
    } else if significant.len() > MAX_SIGNIFICANT_DIGITS {
        TOO_MANY_DIGITS
    } else {
        u64::from_str_radix(significant, radix).unwrap_or(TOO_MANY_DIGITS)
    }
}

fn skip_empty_lines(data: &str, mut pos: usize) -> usize {
    while data[pos..].starts_with(CRLF) {
        pos += 2;
    }
    pos
}

fn check_line_endings(text: &str) -> Result<(), Stop> {
    let rest = text.replace(CRLF, "");
    if rest.contains('\r') || rest.contains('\n') {
        return Err(Stop::Fail("bad-line-ending"));
    }
    Ok(())
}

fn parse_request_line(line: &str) -> Result<Vec<String>, Stop> {
    let parts: Vec<&str> = line.split(' ').collect();
    if parts.len() != 3 {
        return Err(Stop::Fail("bad-request-line"));
    }
    let (method, target, version) = (parts[0], parts[1], parts[2]);
    let valid_target = !target.is_empty() && target.bytes().all(|c| (b'!'..=b'~').contains(&c));
    let v = version.as_bytes();
    let valid_version = v.len() == 8
        && version.starts_with("HTTP/")
        && v[5].is_ascii_digit()
        && v[6] == b'.'
        && v[7].is_ascii_digit();
    if !is_token(method) || !valid_target || !valid_version {
        return Err(Stop::Fail("bad-request-line"));
    }
    Ok(row(&["request", method, target, version]))
}

fn parse_field_line(tag: &str, line: &str) -> Result<Vec<String>, Stop> {
    if line.starts_with(' ') || line.starts_with('\t') {
        return Err(Stop::Fail("obs-fold"));
    }
    let colon = match line.find(':') {
        Some(colon) if is_token(&line[..colon]) => colon,
        _ => return Err(Stop::Fail("bad-field")),
    };
    let value = trim_ows(&line[colon + 1..]);
    if !value.bytes().all(|c| c == b'\t' || (b' '..=b'~').contains(&c)) {
        return Err(Stop::Fail("bad-field"));
    }
    Ok(vec![tag.to_string(), line[..colon].to_ascii_lowercase(), value.to_string()])
}

/// A comma-separated list over every field line, with empty elements dropped.
fn list_elements(values: &[String]) -> Vec<String> {
    values
        .join(",")
        .split(',')
        .map(trim_ows)
        .filter(|element| !element.is_empty())
        .map(str::to_string)
        .collect()
}

fn chunk_size(line: &str) -> Result<u64, Stop> {
    if line.contains('\r') || line.contains('\n') {
        return Err(Stop::Fail("bad-chunk-size"));
    }
    let digits = match line.find(';') {
        Some(semicolon) => line[..semicolon].trim_end_matches(|c| c == ' ' || c == '\t'),
        None => line,
    };
    if digits.is_empty() || !digits.bytes().all(|c| c.is_ascii_hexdigit()) {
        return Err(Stop::Fail("bad-chunk-size"));
    }
    Ok(size_of(digits, 16))
}

/// A request is read in three stages: skip empty lines, find the end of the head (the first
/// CRLF CRLF), then read the body that the framing fields announce. Each stage either finishes,
/// needs more bytes, or fails, and the same code serves the one-shot methods and the connection:
/// `feed` keeps the unread bytes and runs the stages again each time more arrive, so a message is
/// reported by the call that completes it.
pub struct HttpParser {
    head_limit: Option<usize>,
    body_limit: Option<u64>,
    buffer: String,
    closed: bool,
}

impl HttpParser {
    pub fn new() -> Self {
        HttpParser { head_limit: None, body_limit: None, buffer: String::new(), closed: false }
    }

    // Level 1
    pub fn parse_head(&mut self, data: String) -> Vec<Vec<String>> {
        let start = skip_empty_lines(&data, 0);
        let result = self.end_of_head(&data, start).and_then(|end| self.head_rows(&data[start..end - 4]));
        Self::report(result)
    }

    // Level 2
    pub fn parse_message(&mut self, data: String) -> Vec<Vec<String>> {
        let start = skip_empty_lines(&data, 0);
        Self::report(self.message(&data, start).map(|(rows, _)| rows))
    }

    // Level 3
    pub fn feed(&mut self, data: String) -> Vec<Vec<String>> {
        let mut rows = Vec::new();
        if self.closed {
            return rows;
        }
        self.buffer.push_str(&data);
        loop {
            let start = skip_empty_lines(&self.buffer, 0);
            self.buffer.drain(..start);
            match self.message(&self.buffer, 0) {
                Ok((message, end)) => {
                    rows.extend(message);
                    self.buffer.drain(..end);
                }
                Err(Stop::NeedMore) => return rows,
                Err(Stop::Fail(code)) => {
                    self.closed = true;
                    self.buffer.clear();
                    rows.push(row(&["error", code]));
                    return rows;
                }
            }
        }
    }

    pub fn close(&mut self) -> Vec<Vec<String>> {
        if self.closed {
            return Vec::new();
        }
        self.closed = true;
        if self.buffer.is_empty() {
            Vec::new()
        } else {
            vec![row(&["error", "incomplete"])]
        }
    }

    // Level 4
    pub fn set_limits(&mut self, max_head_bytes: i32, max_body_bytes: i32) {
        self.head_limit = Some(max_head_bytes as usize);
        self.body_limit = Some(max_body_bytes as u64);
    }

    // The stages
    fn report(result: Result<Rows, Stop>) -> Rows {
        match result {
            Ok(rows) => rows,
            Err(Stop::NeedMore) => vec![row(&["error", "incomplete"])],
            Err(Stop::Fail(code)) => vec![row(&["error", code])],
        }
    }

    /// The index just after the head's empty line. With a limit, only the first `limit` bytes
    /// are searched, so a head that cannot fit fails without waiting.
    fn end_of_head(&self, data: &str, start: usize) -> Result<usize, Stop> {
        let available = &data[start..];
        let window = match self.head_limit {
            Some(limit) if available.len() > limit => &available[..limit],
            _ => available,
        };
        match window.find(END_OF_HEAD) {
            Some(found) => Ok(start + found + 4),
            None => match self.head_limit {
                Some(limit) if available.len() >= limit => Err(Stop::Fail("head-too-large")),
                _ => Err(Stop::NeedMore),
            },
        }
    }

    fn head_rows(&self, text: &str) -> Result<Rows, Stop> {
        check_line_endings(text)?;
        let mut lines = text.split(CRLF);
        let request = parse_request_line(lines.next().unwrap_or(""))?;
        let http11 = request[3] == "HTTP/1.1";
        let mut rows = vec![request];
        for line in lines {
            rows.push(parse_field_line("field", line)?);
        }
        let hosts = rows[1..].iter().filter(|row| row[1] == "host").count();
        if hosts > 1 || (hosts == 0 && http11) {
            return Err(Stop::Fail("bad-host"));
        }
        Ok(rows)
    }

    fn message(&self, data: &str, start: usize) -> Result<(Rows, usize), Stop> {
        let head_end = self.end_of_head(data, start)?;
        let mut rows = self.head_rows(&data[start..head_end - 4])?;
        let values = |name: &str| -> Vec<String> {
            rows[1..].iter().filter(|row| row[1] == name).map(|row| row[2].clone()).collect()
        };
        let codings = values("transfer-encoding");
        let lengths = values("content-length");
        if !codings.is_empty() && !lengths.is_empty() {
            return Err(Stop::Fail("ambiguous-length"));
        }
        if !codings.is_empty() {
            let list = list_elements(&codings);
            if list.len() != 1 || !list[0].eq_ignore_ascii_case("chunked") {
                return Err(Stop::Fail("unsupported-transfer-coding"));
            }
            return self.chunked(data, head_end, rows);
        }
        let length = if lengths.is_empty() { 0 } else { self.content_length(&lengths)? };
        if ((data.len() - head_end) as u64) < length {
            return Err(Stop::NeedMore);
        }
        let end = head_end + length as usize;
        rows.push(row(&["body", &data[head_end..end]]));
        Ok((rows, end))
    }

    fn content_length(&self, lines: &[String]) -> Result<u64, Stop> {
        let elements = list_elements(lines);
        if elements.is_empty() || !elements.iter().all(|e| e.bytes().all(|c| c.is_ascii_digit())) {
            return Err(Stop::Fail("bad-content-length"));
        }
        let first = elements[0].trim_start_matches('0');
        if elements.iter().any(|element| element.trim_start_matches('0') != first) {
            return Err(Stop::Fail("conflicting-content-length"));
        }
        let length = size_of(&elements[0], 10);
        if self.too_large(length, 0) {
            return Err(Stop::Fail("body-too-large"));
        }
        Ok(length)
    }

    fn too_large(&self, size: u64, used: u64) -> bool {
        self.body_limit.map_or(false, |limit| used + size > limit)
    }

    fn chunked(&self, data: &str, mut pos: usize, mut rows: Rows) -> Result<(Rows, usize), Stop> {
        let mut content = String::new();
        let mut total = 0u64;
        loop {
            let line_end = pos + data[pos..].find(CRLF).ok_or(Stop::NeedMore)?;
            let size = chunk_size(&data[pos..line_end])?;
            if self.too_large(size, total) {
                return Err(Stop::Fail("body-too-large"));
            }
            pos = line_end + 2;
            if size == 0 {
                break;
            }
            if ((data.len() - pos) as u64) < size + 2 {
                return Err(Stop::NeedMore);
            }
            let end = pos + size as usize;
            if &data[end..end + 2] != CRLF {
                return Err(Stop::Fail("bad-chunk"));
            }
            content.push_str(&data[pos..end]);
            total += size;
            pos = end + 2;
        }
        rows.push(vec!["body".to_string(), content]);
        if data[pos..].starts_with(CRLF) {
            return Ok((rows, pos + 2));
        }
        let found = pos + data[pos..].find(END_OF_HEAD).ok_or(Stop::NeedMore)?;
        let text = &data[pos..found];
        check_line_endings(text)?;
        for line in text.split(CRLF) {
            rows.push(parse_field_line("trailer", line)?);
        }
        Ok((rows, found + 4))
    }
}
