use std::cmp::Reverse;
use std::collections::BinaryHeap;

pub fn network_delay_time(times: Vec<Vec<i32>>, n: i32, k: i32) -> i32 {
    let n = n as usize;
    let mut graph: Vec<Vec<(usize, i32)>> = vec![Vec::new(); n + 1];
    for link in &times {
        graph[link[0] as usize].push((link[1] as usize, link[2]));
    }
    let mut settled = vec![false; n + 1];
    let (mut reached, mut latest) = (0, 0);
    // BinaryHeap is a max-heap, so Reverse turns it into a min-heap ordered by time first.
    let mut queue = BinaryHeap::new();
    queue.push(Reverse((0, k as usize)));
    while let Some(Reverse((time, node))) = queue.pop() {
        if settled[node] {
            continue; // an outdated entry: the node was settled earlier with a smaller time
        }
        settled[node] = true;
        reached += 1;
        latest = latest.max(time);
        for &(neighbor, w) in &graph[node] {
            if !settled[neighbor] {
                queue.push(Reverse((time + w, neighbor)));
            }
        }
    }
    if reached == n {
        latest
    } else {
        -1
    }
}
