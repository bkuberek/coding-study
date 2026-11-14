use std::collections::HashMap;

pub fn get_importance(employees: Vec<Vec<i32>>, employee_id: i32) -> i32 {
    let by_id: HashMap<i32, &Vec<i32>> =
        employees.iter().map(|record| (record[0], record)).collect();
    let mut total = 0;
    let mut pending = vec![employee_id];
    while let Some(wanted) = pending.pop() {
        let Some(record) = by_id.get(&wanted) else {
            continue;
        };
        total += record[1];
        pending.extend_from_slice(&record[2..]);
    }
    total
}
