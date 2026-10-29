pub fn can_finish(num_courses: i32, prerequisites: Vec<Vec<i32>>) -> bool {
    let count = num_courses as usize;
    let mut required: Vec<Vec<usize>> = vec![Vec::new(); count];
    for pair in &prerequisites {
        required[pair[0] as usize].push(pair[1] as usize);
    }
    let mut taken = vec![false; count];
    for _ in 0..count {
        // Take the first course whose prerequisites are all done; give up if there is none.
        let next = (0..count)
            .find(|&course| !taken[course] && required[course].iter().all(|&before| taken[before]));
        match next {
            Some(course) => taken[course] = true,
            None => return false,
        }
    }
    true
}
