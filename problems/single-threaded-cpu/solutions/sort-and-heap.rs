use std::cmp::Reverse;
use std::collections::BinaryHeap;

pub fn get_order(tasks: Vec<Vec<i32>>) -> Vec<i32> {
    let mut arrivals: Vec<usize> = (0..tasks.len()).collect();
    arrivals.sort_by_key(|&index| tasks[index][0]);
    // (processing time, index) in a min-heap: ties go to the smaller index.
    let mut waiting: BinaryHeap<Reverse<(i32, usize)>> = BinaryHeap::new();
    let mut time: i64 = 0; // the clock can pass i32::MAX
    let mut next_arrival = 0;
    let mut order = Vec::with_capacity(tasks.len());
    while order.len() < tasks.len() {
        if waiting.is_empty() {
            // Idle until the next arrival.
            time = time.max(i64::from(tasks[arrivals[next_arrival]][0]));
        }
        while next_arrival < tasks.len() && i64::from(tasks[arrivals[next_arrival]][0]) <= time {
            let index = arrivals[next_arrival];
            waiting.push(Reverse((tasks[index][1], index)));
            next_arrival += 1;
        }
        let Reverse((processing, index)) = waiting.pop().expect("a task has arrived");
        time += i64::from(processing);
        order.push(index as i32);
    }
    order
}
