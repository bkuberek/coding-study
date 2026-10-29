const UNVISITED: u8 = 0;
const ON_PATH: u8 = 1;
const DONE: u8 = 2;

/// Whether every prerequisite chain below `course` ends without looping.
fn completes(course: usize, required: &[Vec<usize>], state: &mut [u8]) -> bool {
    state[course] = ON_PATH;
    for &before in &required[course] {
        if state[before] == ON_PATH {
            return false; // the chain came back to a course still being explored
        }
        if state[before] == UNVISITED && !completes(before, required, state) {
            return false;
        }
    }
    state[course] = DONE;
    true
}

pub fn can_finish(num_courses: i32, prerequisites: Vec<Vec<i32>>) -> bool {
    let count = num_courses as usize;
    let mut required: Vec<Vec<usize>> = vec![Vec::new(); count];
    for pair in &prerequisites {
        required[pair[0] as usize].push(pair[1] as usize);
    }
    let mut state = vec![UNVISITED; count];
    (0..count).all(|course| state[course] == DONE || completes(course, &required, &mut state))
}
