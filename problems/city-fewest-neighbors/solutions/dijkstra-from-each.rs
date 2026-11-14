use std::cmp::Reverse;
use std::collections::BinaryHeap;

pub fn find_the_city(n: i32, edges: Vec<Vec<i32>>, distance_threshold: i32) -> i32 {
    let n = n as usize;
    let mut graph: Vec<Vec<(usize, i32)>> = vec![Vec::new(); n];
    for road in &edges {
        let (a, b, w) = (road[0] as usize, road[1] as usize, road[2]);
        graph[a].push((b, w));
        graph[b].push((a, w));
    }

    // Counts the other cities within the threshold, stopping once distances exceed it.
    let reachable = |source: usize| -> usize {
        let mut settled = vec![false; n];
        let mut count = 0;
        // `BinaryHeap` is a max-heap, so `Reverse` makes the nearest city pop first.
        let mut heap = BinaryHeap::new();
        heap.push(Reverse((0, source)));
        while let Some(Reverse((distance, city))) = heap.pop() {
            if distance > distance_threshold {
                break;
            }
            if settled[city] {
                continue;
            }
            settled[city] = true;
            count += 1;
            for &(neighbor, w) in &graph[city] {
                if !settled[neighbor] && distance + w <= distance_threshold {
                    heap.push(Reverse((distance + w, neighbor)));
                }
            }
        }
        count - 1 // the source settles first and is not its own neighbor
    };

    let mut best_city = 0;
    let mut best_count = n + 1;
    for city in 0..n {
        let count = reachable(city);
        // `<=` lets a later city win a tie.
        if count <= best_count {
            best_city = city;
            best_count = count;
        }
    }
    best_city as i32
}
