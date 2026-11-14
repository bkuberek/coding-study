pub fn decode_string(s: String) -> String {
    let mut s = s;
    while s.contains('[') {
        // The first "]" closes an innermost group: the last "[" before it is its opener.
        let closing = s.find(']').unwrap();
        let opening = s[..closing].rfind('[').unwrap();
        let mut start = opening;
        while start > 0 && s.as_bytes()[start - 1].is_ascii_digit() {
            start -= 1;
        }
        let count: usize = s[start..opening].parse().unwrap();
        s = format!(
            "{}{}{}",
            &s[..start],
            s[opening + 1..closing].repeat(count),
            &s[closing + 1..]
        );
    }
    s
}
