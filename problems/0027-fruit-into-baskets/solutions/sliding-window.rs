use std::collections::HashMap;

pub fn total_fruit(fruits: Vec<i32>) -> i32 {
    let mut in_window: HashMap<i32, usize> = HashMap::new();
    let (mut left, mut best) = (0, 0);
    for (right, &fruit) in fruits.iter().enumerate() {
        *in_window.entry(fruit).or_insert(0) += 1;
        while in_window.len() > 2 {
            let leaving = fruits[left];
            if let Some(count) = in_window.get_mut(&leaving) {
                *count -= 1;
                if *count == 0 {
                    in_window.remove(&leaving);
                }
            }
            left += 1;
        }
        best = best.max(right + 1 - left);
    }
    best as i32
}
