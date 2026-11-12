pub fn is_valid_task_order(n: i32, prerequisites: Vec<Vec<i32>>, order: Vec<i32>) -> bool {
    if order.len() != n as usize {
        return false;
    }
    for task in 0..n {
        if order.iter().filter(|&&listed| listed == task).count() != 1 {
            return false;
        }
    }
    for pair in &prerequisites {
        let before = order.iter().position(|&listed| listed == pair[0]);
        let after = order.iter().position(|&listed| listed == pair[1]);
        if before >= after {
            return false;
        }
    }
    true
}
