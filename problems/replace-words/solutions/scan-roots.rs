pub fn replace_words(dictionary: Vec<String>, sentence: String) -> String {
    let shortened: Vec<&str> = sentence
        .split(' ')
        .map(|word| {
            let mut best = word;
            for root in &dictionary {
                if root.len() < best.len() && word.starts_with(root.as_str()) {
                    best = root;
                }
            }
            best
        })
        .collect();
    shortened.join(" ")
}
