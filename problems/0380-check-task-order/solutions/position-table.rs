pub fn is_valid_task_order(n: i32, prerequisites: Vec<Vec<i32>>, order: Vec<i32>) -> bool {
    let n = n as usize;
    if order.len() != n {
        return false;
    }
    // position[t]: where task t stands in the order, or None while it has not been seen.
    let mut position: Vec<Option<usize>> = vec![None; n];
    for (place, &task) in order.iter().enumerate() {
        let slot = &mut position[task as usize];
        if slot.is_some() {
            return false;
        }
        *slot = Some(place);
    }
    prerequisites
        .iter()
        .all(|pair| position[pair[0] as usize] < position[pair[1] as usize])
}
