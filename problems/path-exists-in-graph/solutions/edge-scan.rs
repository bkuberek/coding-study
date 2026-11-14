pub fn has_path(n: i32, edges: Vec<Vec<i32>>, source: i32, target: i32) -> bool {
    let (source, target) = (source as usize, target as usize);
    let mut reached = vec![false; n as usize];
    reached[source] = true;
    let mut changed = true;
    while changed && !reached[target] {
        changed = false;
        for edge in &edges {
            let (a, b) = (edge[0] as usize, edge[1] as usize);
            // A connection with exactly one reached end brings the other end in.
            if reached[a] != reached[b] {
                reached[a] = true;
                reached[b] = true;
                changed = true;
            }
        }
    }
    reached[target]
}
