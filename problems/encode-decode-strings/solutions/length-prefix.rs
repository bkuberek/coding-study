const MARKER: char = '#';

fn encode(strs: &[String]) -> String {
    let mut encoded = String::new();
    for text in strs {
        encoded.push_str(&text.len().to_string());
        encoded.push(MARKER);
        encoded.push_str(text);
    }
    encoded
}

fn decode(encoded: &str) -> Vec<String> {
    let mut strs = Vec::new();
    let mut position = 0;
    while position < encoded.len() {
        // A length has only digits, so the first marker after it ends the length.
        let marker = position
            + encoded[position..]
                .find(MARKER)
                .expect("a chunk has a marker");
        let length: usize = encoded[position..marker]
            .parse()
            .expect("a length is digits");
        let start = marker + 1;
        let end = start + length;
        strs.push(encoded[start..end].to_string());
        position = end;
    }
    strs
}

pub fn encode_decode(strs: Vec<String>) -> Vec<String> {
    decode(&encode(&strs))
}
