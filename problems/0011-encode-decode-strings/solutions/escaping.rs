const ESCAPE: char = '\\';
const TERMINATOR: char = ',';

fn encode(strs: &[String]) -> String {
    let mut encoded = String::new();
    for text in strs {
        for character in text.chars() {
            if character == ESCAPE || character == TERMINATOR {
                encoded.push(ESCAPE);
            }
            encoded.push(character);
        }
        encoded.push(TERMINATOR);
    }
    encoded
}

fn decode(encoded: &str) -> Vec<String> {
    let mut strs = Vec::new();
    let mut current = String::new();
    let mut escaped = false;
    for character in encoded.chars() {
        if escaped {
            current.push(character);
            escaped = false;
        } else if character == ESCAPE {
            escaped = true;
        } else if character == TERMINATOR {
            strs.push(std::mem::take(&mut current));
        } else {
            current.push(character);
        }
    }
    strs
}

pub fn encode_decode(strs: Vec<String>) -> Vec<String> {
    decode(&encode(&strs))
}
