use std::collections::HashSet;

pub struct Trie {
    words: HashSet<String>,
}

impl Trie {
    pub fn new() -> Self {
        Trie {
            words: HashSet::new(),
        }
    }

    pub fn insert(&mut self, word: String) {
        self.words.insert(word);
    }

    pub fn search(&mut self, word: String) -> bool {
        self.words.contains(&word)
    }

    pub fn starts_with(&mut self, prefix: String) -> bool {
        self.words.iter().any(|word| word.starts_with(&prefix))
    }
}
