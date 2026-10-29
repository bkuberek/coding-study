const EMPTY: i32 = -1; // marks an unused basket; fruit types are never negative

pub fn total_fruit(fruits: Vec<i32>) -> i32 {
    let (mut best, mut window) = (0, 0);
    let (mut last, mut before_last) = (EMPTY, EMPTY);
    let mut last_run = 0;
    for fruit in fruits {
        window = if fruit == last || fruit == before_last {
            window + 1
        } else {
            last_run + 1
        };
        if fruit == last {
            last_run += 1;
        } else {
            before_last = last;
            last = fruit;
            last_run = 1;
        }
        best = best.max(window);
    }
    best
}
