pub fn minimum_semesters(n: i32, relations: Vec<Vec<i32>>) -> i32 {
    let n = n as usize;
    let mut unlocks: Vec<Vec<usize>> = vec![Vec::new(); n + 1];
    let mut waiting = vec![0; n + 1];
    for relation in &relations {
        let (before, after) = (relation[0] as usize, relation[1] as usize);
        unlocks[before].push(after);
        waiting[after] += 1;
    }
    let mut semester_courses: Vec<usize> = (1..=n).filter(|&course| waiting[course] == 0).collect();
    let mut semesters = 0;
    let mut taken = 0;
    while !semester_courses.is_empty() {
        semesters += 1;
        taken += semester_courses.len();
        let mut next_semester = Vec::new();
        for &course in &semester_courses {
            for &unlocked in &unlocks[course] {
                waiting[unlocked] -= 1;
                if waiting[unlocked] == 0 {
                    next_semester.push(unlocked);
                }
            }
        }
        semester_courses = next_semester;
    }
    if taken == n {
        semesters
    } else {
        -1
    }
}
