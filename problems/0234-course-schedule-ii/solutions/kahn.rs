use std::collections::VecDeque;

pub fn find_order(num_courses: i32, prerequisites: Vec<Vec<i32>>) -> Vec<i32> {
    let count = num_courses as usize;
    let mut unlocks: Vec<Vec<usize>> = vec![Vec::new(); count];
    let mut waiting = vec![0; count]; // prerequisites each course still waits for
    for pair in &prerequisites {
        let (course, before) = (pair[0] as usize, pair[1] as usize);
        unlocks[before].push(course);
        waiting[course] += 1;
    }
    let mut ready: VecDeque<usize> = (0..count).filter(|&course| waiting[course] == 0).collect();
    let mut order = Vec::with_capacity(count);
    while let Some(course) = ready.pop_front() {
        order.push(course as i32);
        for &unlocked in &unlocks[course] {
            waiting[unlocked] -= 1;
            if waiting[unlocked] == 0 {
                ready.push_back(unlocked);
            }
        }
    }
    // Courses never taken wait, directly or not, on a cycle.
    if order.len() == count {
        order
    } else {
        Vec::new()
    }
}
