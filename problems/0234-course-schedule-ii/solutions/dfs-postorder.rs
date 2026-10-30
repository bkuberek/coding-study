#[derive(Clone, Copy, PartialEq, Eq)]
enum State {
    Unseen,
    Active,
    Done,
}

pub fn find_order(num_courses: i32, prerequisites: Vec<Vec<i32>>) -> Vec<i32> {
    let count = num_courses as usize;
    let mut required: Vec<Vec<usize>> = vec![Vec::new(); count];
    for pair in &prerequisites {
        required[pair[0] as usize].push(pair[1] as usize);
    }
    let mut state = vec![State::Unseen; count];
    let mut cursor = vec![0; count]; // index of the next prerequisite to visit, per course
    let mut order = Vec::with_capacity(count);
    for root in 0..count {
        if state[root] != State::Unseen {
            continue;
        }
        state[root] = State::Active;
        let mut stack = vec![root];
        while let Some(&course) = stack.last() {
            if cursor[course] == required[course].len() {
                // Every prerequisite is already in the order: the course can follow them.
                stack.pop();
                state[course] = State::Done;
                order.push(course as i32);
                continue;
            }
            let before = required[course][cursor[course]];
            cursor[course] += 1;
            match state[before] {
                State::Active => return Vec::new(), // the path loops back to a course still being explored
                State::Unseen => {
                    state[before] = State::Active;
                    stack.push(before);
                }
                State::Done => {}
            }
        }
    }
    order
}
