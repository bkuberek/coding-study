pub fn total_fruit(fruits: Vec<i32>) -> i32 {
    let mut best = 0;
    for start in 0..fruits.len() {
        let first = fruits[start];
        let mut second = None;
        let mut end = start;
        while end < fruits.len() {
            let fruit = fruits[end];
            if fruit != first && Some(fruit) != second {
                if second.is_some() {
                    break;
                }
                second = Some(fruit);
            }
            end += 1;
        }
        best = best.max(end - start);
    }
    best as i32
}
