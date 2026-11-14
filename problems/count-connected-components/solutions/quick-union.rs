fn find(parent: &[usize], mut x: usize) -> usize {
    while parent[x] != x {
        x = parent[x];
    }
    x
}

pub fn count_components(n: i32, edges: Vec<Vec<i32>>) -> i32 {
    let mut parent: Vec<usize> = (0..n as usize).collect(); // parent[x] == x marks a root
    let mut components = n;
    for edge in &edges {
        let (root_a, root_b) = (
            find(&parent, edge[0] as usize),
            find(&parent, edge[1] as usize),
        );
        if root_a != root_b {
            parent[root_a] = root_b; // no balancing: trees can grow into long chains
            components -= 1;
        }
    }
    components
}
