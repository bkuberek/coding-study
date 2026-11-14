use std::collections::VecDeque;

fn one_apart(first: &str, second: &str) -> bool {
    let mut differences = 0;
    for (a, b) in first.bytes().zip(second.bytes()) {
        if a != b {
            differences += 1;
            if differences > 1 {
                return false;
            }
        }
    }
    differences == 1
}

pub fn ladder_length(begin_word: String, end_word: String, word_list: Vec<String>) -> i32 {
    if !word_list.contains(&end_word) {
        return 0;
    }
    let mut unvisited: Vec<String> = word_list
        .into_iter()
        .filter(|word| *word != begin_word)
        .collect();
    let mut queue = VecDeque::from([(begin_word, 1)]);
    while let Some((word, words_so_far)) = queue.pop_front() {
        if word == end_word {
            return words_so_far;
        }
        // Compare against every word not reached yet; the neighbors leave the list.
        let mut remaining = Vec::with_capacity(unvisited.len());
        for candidate in unvisited {
            if one_apart(&word, &candidate) {
                queue.push_back((candidate, words_so_far + 1));
            } else {
                remaining.push(candidate);
            }
        }
        unvisited = remaining;
    }
    0
}
