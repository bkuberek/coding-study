pub fn count_by_prefix(words: Vec<String>, prefixes: Vec<String>) -> Vec<i32> {
    prefixes
        .iter()
        .map(|prefix| {
            words
                .iter()
                .filter(|word| word.starts_with(prefix.as_str()))
                .count() as i32
        })
        .collect()
}
