pub fn interval_intersection(
    first_list: Vec<Vec<i32>>,
    second_list: Vec<Vec<i32>>,
) -> Vec<Vec<i32>> {
    let mut common = Vec::new();
    let (mut i, mut j) = (0, 0);
    while i < first_list.len() && j < second_list.len() {
        let start = first_list[i][0].max(second_list[j][0]);
        let end = first_list[i][1].min(second_list[j][1]);
        if start <= end {
            common.push(vec![start, end]);
        }
        // The interval that ends first cannot meet anything later in the other list.
        if first_list[i][1] < second_list[j][1] {
            i += 1;
        } else {
            j += 1;
        }
    }
    common
}
