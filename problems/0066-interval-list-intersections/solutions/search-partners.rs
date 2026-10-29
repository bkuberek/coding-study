pub fn interval_intersection(
    first_list: Vec<Vec<i32>>,
    second_list: Vec<Vec<i32>>,
) -> Vec<Vec<i32>> {
    let mut common = Vec::new();
    for first in &first_list {
        let (first_start, first_end) = (first[0], first[1]);
        // The first interval of second_list that ends at or after first_start.
        let partner = second_list.partition_point(|second| second[1] < first_start);
        for second in second_list[partner..]
            .iter()
            .take_while(|second| second[0] <= first_end)
        {
            common.push(vec![first_start.max(second[0]), first_end.min(second[1])]);
        }
    }
    common
}
