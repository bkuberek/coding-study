use std::collections::HashMap;

pub fn group_anagrams(strs: Vec<String>) -> Vec<Vec<String>> {
    let mut groups: HashMap<Vec<u8>, Vec<String>> = HashMap::new();
    for word in strs {
        let mut key = word.as_bytes().to_vec();
        key.sort_unstable();
        groups.entry(key).or_default().push(word);
    }
    groups.into_values().collect()
}
