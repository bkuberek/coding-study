fn find(parent: &[usize], mut x: usize) -> usize {
    while parent[x] != x {
        x = parent[x];
    }
    x
}

pub fn smallest_string_with_swaps(s: String, pairs: Vec<Vec<i32>>) -> String {
    let mut parent: Vec<usize> = (0..s.len()).collect(); // parent[x] == x marks a root
    for pair in &pairs {
        let (root_a, root_b) = (
            find(&parent, pair[0] as usize),
            find(&parent, pair[1] as usize),
        );
        if root_a != root_b {
            parent[root_a] = root_b; // no balancing: trees can grow into long chains
        }
    }

    // Positions are visited in increasing order, so each group's list is sorted.
    let mut groups: Vec<Vec<usize>> = vec![Vec::new(); s.len()];
    for position in 0..s.len() {
        groups[find(&parent, position)].push(position);
    }
    let original = s.as_bytes();
    let mut letters = original.to_vec();
    for positions in &groups {
        let mut sorted: Vec<u8> = positions.iter().map(|&p| original[p]).collect();
        sorted.sort_unstable();
        for (&position, letter) in positions.iter().zip(sorted) {
            letters[position] = letter;
        }
    }
    String::from_utf8(letters).unwrap()
}
