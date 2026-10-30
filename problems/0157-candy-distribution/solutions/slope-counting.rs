pub fn candy(ratings: Vec<i32>) -> i32 {
    let mut total = 1;
    // Length of the current rising run: the latest child got up + 1 candies.
    let mut up = 0;
    // Length of the current falling run.
    let mut down = 0;
    // The rising run length at the top of the current peak.
    let mut peak = 0;
    for pair in ratings.windows(2) {
        if pair[1] > pair[0] {
            up += 1;
            peak = up;
            down = 0;
            total += up + 1;
        } else if pair[1] == pair[0] {
            up = 0;
            down = 0;
            peak = 0;
            total += 1;
        } else {
            up = 0;
            down += 1;
            // Every child on the falling run gets one more candy; the peak only needs one
            // more once the falling run is longer than the rising run that built it.
            total += down + i32::from(down > peak);
        }
    }
    total
}
