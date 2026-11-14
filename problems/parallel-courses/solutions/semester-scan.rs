pub fn minimum_semesters(n: i32, relations: Vec<Vec<i32>>) -> i32 {
    let n = n as usize;
    let mut required: Vec<Vec<usize>> = vec![Vec::new(); n + 1];
    for relation in &relations {
        required[relation[1] as usize].push(relation[0] as usize);
    }
    let mut finished_in = vec![0; n + 1]; // semester a course was taken in; 0 while not taken
    let mut done = 0;
    let mut semester = 0;
    while done < n {
        semester += 1;
        // Free courses need every prerequisite finished in an earlier semester.
        let free: Vec<usize> = (1..=n)
            .filter(|&course| {
                finished_in[course] == 0
                    && required[course]
                        .iter()
                        .all(|&before| 0 < finished_in[before] && finished_in[before] < semester)
            })
            .collect();
        if free.is_empty() {
            return -1;
        }
        for &course in &free {
            finished_in[course] = semester;
        }
        done += free.len();
    }
    semester
}
