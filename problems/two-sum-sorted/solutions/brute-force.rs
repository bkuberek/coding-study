pub fn two_sum_sorted(numbers: Vec<i32>, target: i32) -> Vec<i32> {
    for (i, &value) in numbers.iter().enumerate() {
        let complement = target - value;
        if let Some(offset) = numbers[i + 1..]
            .iter()
            .position(|&later| later == complement)
        {
            return vec![i as i32, (i + 1 + offset) as i32];
        }
    }
    vec![]
}
