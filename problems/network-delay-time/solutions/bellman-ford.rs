const UNREACHED: i32 = i32::MAX;

pub fn network_delay_time(times: Vec<Vec<i32>>, n: i32, k: i32) -> i32 {
    let n = n as usize;
    let mut arrival = vec![UNREACHED; n + 1];
    arrival[k as usize] = 0;
    // After round i, every node whose fastest route uses at most i links has its final time;
    // a fastest route has at most n - 1 links, and a round without changes ends early.
    for _ in 1..n {
        let mut changed = false;
        for link in &times {
            let (u, v, w) = (link[0] as usize, link[1] as usize, link[2]);
            // An unreached node offers nothing, and adding to the marker would overflow.
            if arrival[u] != UNREACHED && arrival[u] + w < arrival[v] {
                arrival[v] = arrival[u] + w;
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }
    let latest = arrival[1..].iter().copied().max().unwrap_or(0);
    if latest == UNREACHED {
        -1
    } else {
        latest
    }
}
