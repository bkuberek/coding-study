pub fn critical_connections(n: i32, connections: Vec<Vec<i32>>) -> Vec<Vec<i32>> {
    let n = n as usize;
    // Each entry is (neighbor, cable index), seen from one end of the cable.
    let mut adjacency: Vec<Vec<(usize, usize)>> = vec![Vec::new(); n];
    for (index, cable) in connections.iter().enumerate() {
        let (a, b) = (cable[0] as usize, cable[1] as usize);
        adjacency[a].push((b, index));
        adjacency[b].push((a, index));
    }

    // Can every server still be reached from server 0 when cable `skipped` is cut?
    let connected_without = |skipped: usize| -> bool {
        let mut seen = vec![false; n];
        seen[0] = true;
        let mut stack = vec![0];
        let mut reached = 1;
        while let Some(server) = stack.pop() {
            for &(neighbor, index) in &adjacency[server] {
                if index != skipped && !seen[neighbor] {
                    seen[neighbor] = true;
                    reached += 1;
                    stack.push(neighbor);
                }
            }
        }
        reached == n
    };

    connections
        .into_iter()
        .enumerate()
        .filter(|&(index, _)| !connected_without(index))
        .map(|(_, cable)| cable)
        .collect()
}
