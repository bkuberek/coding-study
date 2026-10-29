use std::collections::VecDeque;

pub fn can_finish(num_courses: i32, prerequisites: Vec<Vec<i32>>) -> bool {
    let count = num_courses as usize;
    let mut unlocks: Vec<Vec<usize>> = vec![Vec::new(); count];
    let mut waiting = vec![0; count]; // prerequisites each course still waits for
    for pair in &prerequisites {
        let (course, before) = (pair[0] as usize, pair[1] as usize);
        unlocks[before].push(course);
        waiting[course] += 1;
    }
    let mut ready: VecDeque<usize> = (0..count).filter(|&course| waiting[course] == 0).collect();
    let mut taken = 0;
    while let Some(course) = ready.pop_front() {
        taken += 1;
        for &unlocked in &unlocks[course] {
            waiting[unlocked] -= 1;
            if waiting[unlocked] == 0 {
                ready.push_back(unlocked);
            }
        }
    }
    // Courses never taken wait, directly or not, on a cycle.
    taken == count
}
