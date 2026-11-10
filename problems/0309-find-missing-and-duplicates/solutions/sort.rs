pub fn find_missing_and_duplicates(mut nums: Vec<i32>) -> Vec<Vec<i32>> {
    nums.sort_unstable();
    let mut missing = Vec::new();
    let mut duplicated: Vec<i32> = Vec::new();
    let mut expected = 1; // the smallest value not accounted for yet
    let mut previous = 0;
    for &value in &nums {
        if value == previous {
            // A third copy must not list the value again.
            if duplicated.last() != Some(&value) {
                duplicated.push(value);
            }
            continue;
        }
        missing.extend(expected..value);
        expected = value + 1;
        previous = value;
    }
    missing.extend(expected..=nums.len() as i32);
    vec![missing, duplicated]
}
