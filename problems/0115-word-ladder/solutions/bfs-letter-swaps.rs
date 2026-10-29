use std::collections::{HashSet, VecDeque};

pub fn ladder_length(begin_word: String, end_word: String, word_list: Vec<String>) -> i32 {
    // Words still available; a word leaves the set the moment it is reached.
    let mut available: HashSet<String> = word_list.into_iter().collect();
    if !available.contains(&end_word) {
        return 0;
    }
    available.remove(&begin_word);
    let mut queue = VecDeque::from([(begin_word, 1)]);
    while let Some((word, words_so_far)) = queue.pop_front() {
        if word == end_word {
            return words_so_far;
        }
        let mut letters = word.into_bytes();
        for position in 0..letters.len() {
            let original = letters[position];
            for letter in b'a'..=b'z' {
                letters[position] = letter;
                let candidate = std::str::from_utf8(&letters).unwrap();
                if let Some(candidate) = available.take(candidate) {
                    queue.push_back((candidate, words_so_far + 1));
                }
            }
            letters[position] = original;
        }
    }
    0
}
