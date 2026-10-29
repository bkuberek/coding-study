pub fn group_anagrams(strs: Vec<String>) -> Vec<Vec<String>> {
    let mut keys: Vec<Vec<u8>> = Vec::new();
    let mut groups: Vec<Vec<String>> = Vec::new();
    for word in strs {
        let mut key = word.as_bytes().to_vec();
        key.sort_unstable();
        match keys.iter().position(|known| *known == key) {
            Some(index) => groups[index].push(word),
            None => {
                keys.push(key);
                groups.push(vec![word]);
            }
        }
    }
    groups
}
