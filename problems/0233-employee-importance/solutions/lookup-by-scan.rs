pub fn get_importance(employees: Vec<Vec<i32>>, employee_id: i32) -> i32 {
    let mut total = 0;
    let mut pending = vec![employee_id];
    while let Some(wanted) = pending.pop() {
        let Some(record) = employees.iter().find(|record| record[0] == wanted) else {
            continue;
        };
        total += record[1];
        pending.extend_from_slice(&record[2..]);
    }
    total
}
