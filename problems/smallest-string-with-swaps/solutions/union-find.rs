fn find(parent: &mut [usize], mut x: usize) -> usize {
    let mut root = x;
    while parent[root] != root {
        root = parent[root];
    }
    while parent[x] != root {
        // path compression: point the whole path at the root
        let next = parent[x];
        parent[x] = root;
        x = next;
    }
    root
}

pub fn smallest_string_with_swaps(s: String, pairs: Vec<Vec<i32>>) -> String {
    let mut parent: Vec<usize> = (0..s.len()).collect();
    let mut size = vec![1; s.len()]; // size[r]: number of positions in the tree rooted at r
    for pair in &pairs {
        let mut root_a = find(&mut parent, pair[0] as usize);
        let mut root_b = find(&mut parent, pair[1] as usize);
        if root_a == root_b {
            continue;
        }
        if size[root_a] < size[root_b] {
            std::mem::swap(&mut root_a, &mut root_b);
        }
        parent[root_b] = root_a; // union by size: the smaller tree goes under the larger
        size[root_a] += size[root_b];
    }

    // Positions are visited in increasing order, so each group's list is sorted.
    let mut groups: Vec<Vec<usize>> = vec![Vec::new(); s.len()];
    for position in 0..s.len() {
        groups[find(&mut parent, position)].push(position);
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
