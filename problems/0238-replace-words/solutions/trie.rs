#[derive(Default)]
struct TrieNode {
    children: [Option<Box<TrieNode>>; 26],
    /// A root ends at this node.
    end: bool,
}

pub fn replace_words(dictionary: Vec<String>, sentence: String) -> String {
    let mut root = TrieNode::default();
    for word in &dictionary {
        let mut node = &mut root;
        for letter in word.bytes() {
            node = node.children[usize::from(letter - b'a')].get_or_insert_with(Box::default);
        }
        node.end = true;
    }
    let shortened: Vec<&str> = sentence
        .split(' ')
        .map(|word| shorten(&root, word))
        .collect();
    shortened.join(" ")
}

/// The shortest root that prefixes `word`, or `word` itself.
fn shorten<'a>(root: &TrieNode, word: &'a str) -> &'a str {
    let mut node = root;
    for (length, letter) in word.bytes().enumerate() {
        if node.end {
            return &word[..length];
        }
        match &node.children[usize::from(letter - b'a')] {
            Some(child) => node = child,
            None => return word,
        }
    }
    word
}
