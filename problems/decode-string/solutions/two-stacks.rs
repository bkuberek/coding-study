pub fn decode_string(s: String) -> String {
    // For every open group: its repeat count and the text built before its "[".
    let mut counts: Vec<usize> = Vec::new();
    let mut outer_texts: Vec<String> = Vec::new();
    let mut current = String::new();
    let mut count = 0;
    for character in s.bytes() {
        match character {
            b'0'..=b'9' => count = count * 10 + usize::from(character - b'0'),
            b'[' => {
                counts.push(count);
                outer_texts.push(std::mem::take(&mut current));
                count = 0;
            }
            b']' => {
                let mut outer = outer_texts.pop().unwrap();
                outer.push_str(&current.repeat(counts.pop().unwrap()));
                current = outer;
            }
            _ => current.push(char::from(character)),
        }
    }
    current
}
