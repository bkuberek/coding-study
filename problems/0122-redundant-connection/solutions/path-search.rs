use std::collections::HashSet;

fn connected(neighbors: &[Vec<usize>], start: usize, goal: usize) -> bool {
    let mut seen = HashSet::from([start]);
    let mut stack = vec![start];
    while let Some(node) = stack.pop() {
        if node == goal {
            return true;
        }
        for &neighbor in &neighbors[node] {
            if seen.insert(neighbor) {
                stack.push(neighbor);
            }
        }
    }
    false
}

pub fn find_redundant_connection(edges: Vec<Vec<i32>>) -> Vec<i32> {
    let mut neighbors: Vec<Vec<usize>> = vec![Vec::new(); edges.len() + 1];
    for edge in &edges {
        let (a, b) = (edge[0] as usize, edge[1] as usize);
        // The first edge whose ends are already connected closes the only cycle.
        if connected(&neighbors, a, b) {
            return edge.clone();
        }
        neighbors[a].push(b);
        neighbors[b].push(a);
    }
    vec![]
}
