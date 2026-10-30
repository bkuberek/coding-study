pub fn get_order(tasks: Vec<Vec<i32>>) -> Vec<i32> {
    let mut remaining: Vec<usize> = (0..tasks.len()).collect(); // unprocessed indexes, ascending
    let mut time: i64 = 0; // the clock can pass i32::MAX
    let mut order = Vec::with_capacity(tasks.len());
    while !remaining.is_empty() {
        // Scan every waiting task; `min_by_key` keeps the first minimum, so equal processing
        // times go to the smaller index.
        let best = remaining
            .iter()
            .enumerate()
            .filter(|&(_, &index)| i64::from(tasks[index][0]) <= time)
            .min_by_key(|&(_, &index)| tasks[index][1])
            .map(|(position, _)| position);
        let Some(best) = best else {
            // Idle until the next arrival.
            time = remaining
                .iter()
                .map(|&index| i64::from(tasks[index][0]))
                .min()
                .expect("a task remains");
            continue;
        };
        let index = remaining.remove(best);
        time += i64::from(tasks[index][1]);
        order.push(index as i32);
    }
    order
}
