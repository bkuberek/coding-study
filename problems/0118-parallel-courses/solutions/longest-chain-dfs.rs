const ON_PATH: i32 = -1; // marks a course whose chain length is still being computed

/// The longest chain ending at `course`, or -1 if its prerequisites loop.
fn chain_length(course: usize, required: &[Vec<usize>], chain: &mut [i32]) -> i32 {
    if chain[course] == ON_PATH {
        return -1;
    }
    if chain[course] > 0 {
        return chain[course];
    }
    chain[course] = ON_PATH;
    let mut longest = 0;
    for &before in &required[course] {
        let length = chain_length(before, required, chain);
        if length < 0 {
            return -1;
        }
        longest = longest.max(length);
    }
    chain[course] = longest + 1;
    chain[course]
}

pub fn minimum_semesters(n: i32, relations: Vec<Vec<i32>>) -> i32 {
    let n = n as usize;
    let mut required: Vec<Vec<usize>> = vec![Vec::new(); n + 1];
    for relation in &relations {
        required[relation[1] as usize].push(relation[0] as usize);
    }
    // chain[c]: courses on the longest prerequisite chain ending at c; 0 = not computed yet.
    let mut chain = vec![0; n + 1];
    let mut semesters = 0;
    for course in 1..=n {
        let length = chain_length(course, &required, &mut chain);
        if length < 0 {
            return -1;
        }
        semesters = semesters.max(length);
    }
    semesters
}
