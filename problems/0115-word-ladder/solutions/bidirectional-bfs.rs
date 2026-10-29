use std::collections::HashSet;

pub fn ladder_length(begin_word: String, end_word: String, word_list: Vec<String>) -> i32 {
    let mut available: HashSet<String> = word_list.into_iter().collect();
    if !available.contains(&end_word) {
        return 0;
    }
    available.remove(&begin_word);
    available.remove(&end_word);
    // Two frontiers grow toward each other; words counts the ladder length covered so far.
    let mut near = HashSet::from([begin_word]);
    let mut far = HashSet::from([end_word]);
    let mut words = 1;
    while !near.is_empty() && !far.is_empty() {
        if near.len() > far.len() {
            std::mem::swap(&mut near, &mut far); // always expand the smaller frontier
        }
        words += 1;
        let mut following_level = HashSet::new();
        for word in &near {
            let mut letters = word.clone().into_bytes();
            for position in 0..letters.len() {
                let original = letters[position];
                for letter in b'a'..=b'z' {
                    letters[position] = letter;
                    let candidate = std::str::from_utf8(&letters).unwrap();
                    if far.contains(candidate) {
                        return words;
                    }
                    if let Some(candidate) = available.take(candidate) {
                        following_level.insert(candidate);
                    }
                }
                letters[position] = original;
            }
        }
        near = following_level;
    }
    0
}
