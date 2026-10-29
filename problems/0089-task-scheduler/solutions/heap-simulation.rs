use std::collections::{BinaryHeap, VecDeque};

pub fn least_interval(tasks: Vec<char>, cooldown: i32) -> i32 {
    let mut counts = [0; 26];
    for task in tasks {
        counts[(task as u8 - b'A') as usize] += 1;
    }
    // Max-heap of remaining counts for the tasks that may run now.
    let mut ready: BinaryHeap<i32> = counts.into_iter().filter(|&count| count > 0).collect();
    // Tasks that just ran, as (time they may run again, copies left). Times are pushed in
    // increasing order, so the front is always the next to come back.
    let mut cooling: VecDeque<(i32, i32)> = VecDeque::new();
    let mut time = 0;
    while !ready.is_empty() || !cooling.is_empty() {
        if let Some(count) = ready.pop() {
            if count > 1 {
                cooling.push_back((time + cooldown + 1, count - 1));
            }
            time += 1;
        } else {
            time = cooling[0].0; // nothing can run: skip the idle stretch at once
        }
        while cooling
            .front()
            .is_some_and(|&(ready_at, _)| ready_at <= time)
        {
            if let Some((_, remaining)) = cooling.pop_front() {
                ready.push(remaining);
            }
        }
    }
    time
}
