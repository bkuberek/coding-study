pub fn rob(nums: Vec<i32>) -> i32 {
    // Before each house: without_last and with_last are the best totals for the prefixes
    // that end two houses back and one house back.
    let (mut without_last, mut with_last) = (0, 0);
    for cash in nums {
        (without_last, with_last) = (with_last, with_last.max(without_last + cash));
    }
    with_last
}
