pub fn interval_intersection(
    first_list: Vec<Vec<i32>>,
    second_list: Vec<Vec<i32>>,
) -> Vec<Vec<i32>> {
    // Both lists are sorted and separate, so pairs taken in this order yield sorted output.
    let mut common = Vec::new();
    for first in &first_list {
        for second in &second_list {
            let (start, end) = (first[0].max(second[0]), first[1].min(second[1]));
            if start <= end {
                common.push(vec![start, end]);
            }
        }
    }
    common
}
