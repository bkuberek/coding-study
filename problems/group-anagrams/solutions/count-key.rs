use std::collections::HashMap;

const ALPHABET_SIZE: usize = 26;

pub fn group_anagrams(strs: Vec<String>) -> Vec<Vec<String>> {
    let mut groups: HashMap<[u32; ALPHABET_SIZE], Vec<String>> = HashMap::new();
    for word in strs {
        // Arrays implement `Hash` and `Eq`, so the 26 counts are the map key themselves.
        let mut counts = [0u32; ALPHABET_SIZE];
        for letter in word.bytes() {
            counts[usize::from(letter - b'a')] += 1;
        }
        groups.entry(counts).or_default().push(word);
    }
    groups.into_values().collect()
}
