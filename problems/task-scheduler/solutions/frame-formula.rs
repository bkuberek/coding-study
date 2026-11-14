pub fn least_interval(tasks: Vec<char>, cooldown: i32) -> i32 {
    let mut counts = [0; 26];
    for &task in &tasks {
        counts[(task as u8 - b'A') as usize] += 1;
    }
    let top = counts.into_iter().max().unwrap_or(0);
    let tied = counts.iter().filter(|&&count| count == top).count() as i32;
    // top - 1 full frames of cooldown + 1 slots, then one last partial frame holding the
    // tied most frequent tasks. With enough other tasks, no slot idles and the answer is
    // simply the number of tasks.
    (tasks.len() as i32).max((top - 1) * (cooldown + 1) + tied)
}
