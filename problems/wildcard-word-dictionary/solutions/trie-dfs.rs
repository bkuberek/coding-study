const ALPHABET_SIZE: usize = 26;
const WILDCARD: u8 = b'.';

#[derive(Default)]
struct Node {
    children: [Option<Box<Node>>; ALPHABET_SIZE],
    is_word: bool,
}

pub struct WordDictionary {
    root: Node,
}

impl WordDictionary {
    pub fn new() -> Self {
        WordDictionary {
            root: Node::default(),
        }
    }

    pub fn add_word(&mut self, word: String) {
        let mut node = &mut self.root;
        for letter in word.bytes() {
            node = node.children[slot(letter)].get_or_insert_with(Box::default);
        }
        node.is_word = true;
    }

    pub fn search(&mut self, word: String) -> bool {
        matches_from(&self.root, word.as_bytes())
    }
}

/// Does some stored word continue from `node` the way `pattern` says?
fn matches_from(mut node: &Node, pattern: &[u8]) -> bool {
    for (at, &wanted) in pattern.iter().enumerate() {
        if wanted == WILDCARD {
            return node
                .children
                .iter()
                .flatten()
                .any(|child| matches_from(child, &pattern[at + 1..]));
        }
        match node.children[slot(wanted)].as_deref() {
            Some(child) => node = child,
            None => return false,
        }
    }
    node.is_word
}

fn slot(letter: u8) -> usize {
    usize::from(letter - b'a')
}
