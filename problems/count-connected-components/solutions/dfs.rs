pub fn count_components(n: i32, edges: Vec<Vec<i32>>) -> i32 {
    let n = n as usize;
    let mut neighbors: Vec<Vec<usize>> = vec![Vec::new(); n];
    for edge in &edges {
        let (a, b) = (edge[0] as usize, edge[1] as usize);
        neighbors[a].push(b);
        neighbors[b].push(a);
    }
    let mut seen = vec![false; n];
    let mut components = 0;
    for start in 0..n {
        if seen[start] {
            continue;
        }
        components += 1;
        seen[start] = true;
        let mut stack = vec![start]; // an explicit stack avoids deep recursion on long paths
        while let Some(node) = stack.pop() {
            for &neighbor in &neighbors[node] {
                if !seen[neighbor] {
                    seen[neighbor] = true;
                    stack.push(neighbor);
                }
            }
        }
    }
    components
}
