const ALPHABET_SIZE: usize = 26;

#[derive(Default)]
struct Node {
    children: [Option<Box<Node>>; ALPHABET_SIZE],
    passing: i32, // how many words go through this node
}

pub fn count_by_prefix(words: Vec<String>, prefixes: Vec<String>) -> Vec<i32> {
    let mut root = Node::default();
    for word in &words {
        let mut node = &mut root;
        for letter in word.bytes() {
            node = node.children[slot(letter)].get_or_insert_with(Box::default);
            node.passing += 1;
        }
    }

    prefixes
        .iter()
        .map(|prefix| count_below(&root, prefix))
        .collect()
}

/// The counter at the end of the path spelled by `prefix`, or 0 if the path breaks off.
fn count_below(root: &Node, prefix: &str) -> i32 {
    let mut node = root;
    for letter in prefix.bytes() {
        match node.children[slot(letter)].as_deref() {
            Some(child) => node = child,
            None => return 0,
        }
    }
    node.passing
}

fn slot(letter: u8) -> usize {
    usize::from(letter - b'a')
}
