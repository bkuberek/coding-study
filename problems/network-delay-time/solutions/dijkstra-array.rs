const UNREACHED: i32 = i32::MAX;

pub fn network_delay_time(times: Vec<Vec<i32>>, n: i32, k: i32) -> i32 {
    let n = n as usize;
    let mut graph: Vec<Vec<(usize, i32)>> = vec![Vec::new(); n + 1];
    for link in &times {
        graph[link[0] as usize].push((link[1] as usize, link[2]));
    }
    let mut arrival = vec![UNREACHED; n + 1];
    arrival[k as usize] = 0;
    let mut settled = vec![false; n + 1];
    let mut latest = 0;
    for _ in 0..n {
        // Scan for the unsettled node with the earliest arrival: O(n) per round, no heap.
        let node = (1..=n)
            .filter(|&candidate| !settled[candidate])
            .min_by_key(|&candidate| arrival[candidate])
            .expect("every round settles one of n nodes, so an unsettled node remains");
        if arrival[node] == UNREACHED {
            return -1;
        }
        settled[node] = true;
        latest = arrival[node];
        for &(neighbor, w) in &graph[node] {
            arrival[neighbor] = arrival[neighbor].min(arrival[node] + w);
        }
    }
    latest
}
