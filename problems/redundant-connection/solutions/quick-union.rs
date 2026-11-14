fn find(parent: &[usize], mut x: usize) -> usize {
    while parent[x] != x {
        x = parent[x];
    }
    x
}

pub fn find_redundant_connection(edges: Vec<Vec<i32>>) -> Vec<i32> {
    let mut parent: Vec<usize> = (0..=edges.len()).collect(); // parent[x] == x marks a root
    for edge in &edges {
        let (root_a, root_b) = (
            find(&parent, edge[0] as usize),
            find(&parent, edge[1] as usize),
        );
        if root_a == root_b {
            return edge.clone(); // the ends are already connected: this edge closes the cycle
        }
        parent[root_a] = root_b; // no balancing: trees can grow into long chains
    }
    vec![]
}
