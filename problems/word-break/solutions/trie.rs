#[derive(Default)]
struct TrieNode {
    children: [Option<Box<TrieNode>>; 26],
    ends_word: bool,
}

pub fn word_break(s: String, word_dict: Vec<String>) -> bool {
    let mut root = TrieNode::default();
    for word in &word_dict {
        let mut node = &mut root;
        for letter in word.bytes() {
            node = node.children[(letter - b'a') as usize].get_or_insert_with(Box::default);
        }
        node.ends_word = true;
    }

    let letters = s.as_bytes();
    // reachable[i] is true when the prefix s[..i] can be split into dictionary words.
    let mut reachable = vec![false; letters.len() + 1];
    reachable[0] = true;
    for start in 0..letters.len() {
        if !reachable[start] {
            continue;
        }
        let mut node = &root;
        for position in start..letters.len() {
            match &node.children[(letters[position] - b'a') as usize] {
                Some(child) => node = child,
                None => break,
            }
            if node.ends_word {
                reachable[position + 1] = true;
            }
        }
    }
    reachable[letters.len()]
}
