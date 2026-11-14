use std::cmp::Reverse;
use std::collections::BinaryHeap;

pub fn employee_free_time(schedule: Vec<Vec<Vec<i32>>>) -> Vec<Vec<i32>> {
    // One entry per employee: the start of their next interval, who they are, and its position.
    let mut upcoming: BinaryHeap<Reverse<(i32, usize, usize)>> = schedule
        .iter()
        .enumerate()
        .map(|(person, shifts)| Reverse((shifts[0][0], person, 0)))
        .collect();
    let mut free = Vec::new();
    let mut busy_until = upcoming.peek().map_or(0, |Reverse((start, _, _))| *start);
    while let Some(Reverse((start, person, position))) = upcoming.pop() {
        if start > busy_until {
            free.push(vec![busy_until, start]);
        }
        busy_until = busy_until.max(schedule[person][position][1]);
        if let Some(next) = schedule[person].get(position + 1) {
            upcoming.push(Reverse((next[0], person, position + 1)));
        }
    }
    free
}
