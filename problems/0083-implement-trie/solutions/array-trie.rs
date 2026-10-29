const ALPHABET_SIZE: usize = 26;

#[derive(Default)]
struct Node {
    children: [Option<Box<Node>>; ALPHABET_SIZE],
    is_word: bool,
}

pub struct Trie {
    root: Node,
}

impl Trie {
    pub fn new() -> Self {
        Trie {
            root: Node::default(),
        }
    }

    pub fn insert(&mut self, word: String) {
        let mut node = &mut self.root;
        for letter in word.bytes() {
            node = node.children[slot(letter)].get_or_insert_with(Box::default);
        }
        node.is_word = true;
    }

    pub fn search(&mut self, word: String) -> bool {
        self.walk(&word).is_some_and(|node| node.is_word)
    }

    pub fn starts_with(&mut self, prefix: String) -> bool {
        self.walk(&prefix).is_some()
    }

    /// The node at the end of the path spelled by `text`, or `None` if the path breaks off.
    fn walk(&self, text: &str) -> Option<&Node> {
        let mut node = &self.root;
        for letter in text.bytes() {
            node = node.children[slot(letter)].as_deref()?;
        }
        Some(node)
    }
}

fn slot(letter: u8) -> usize {
    usize::from(letter - b'a')
}
