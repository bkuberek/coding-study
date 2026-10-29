use std::collections::{HashMap, HashSet};

const WILDCARD: u8 = b'.';

pub struct WordDictionary {
    by_length: HashMap<usize, HashSet<String>>,
}

impl WordDictionary {
    pub fn new() -> Self {
        WordDictionary {
            by_length: HashMap::new(),
        }
    }

    pub fn add_word(&mut self, word: String) {
        self.by_length.entry(word.len()).or_default().insert(word);
    }

    pub fn search(&mut self, word: String) -> bool {
        let Some(candidates) = self.by_length.get(&word.len()) else {
            return false;
        };
        if !word.bytes().any(|letter| letter == WILDCARD) {
            return candidates.contains(&word);
        }
        candidates.iter().any(|candidate| matches(&word, candidate))
    }
}

/// Compares a pattern with a stored word of the same length.
fn matches(pattern: &str, word: &str) -> bool {
    pattern
        .bytes()
        .zip(word.bytes())
        .all(|(wanted, letter)| wanted == WILDCARD || wanted == letter)
}
