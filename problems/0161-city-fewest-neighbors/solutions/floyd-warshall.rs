/// Marks a missing road; half of `i32::MAX` keeps the sum of two of them from overflowing.
const INF: i32 = i32::MAX / 2;

pub fn find_the_city(n: i32, edges: Vec<Vec<i32>>, distance_threshold: i32) -> i32 {
    let n = n as usize;
    let mut dist = vec![vec![INF; n]; n];
    for (city, row) in dist.iter_mut().enumerate() {
        row[city] = 0;
    }
    for road in &edges {
        let (a, b, w) = (road[0] as usize, road[1] as usize, road[2]);
        dist[a][b] = w;
        dist[b][a] = w;
    }
    // After step `middle`, dist[i][j] is the shortest route that only passes through cities 0..=middle.
    for middle in 0..n {
        let through = dist[middle].clone();
        for row in dist.iter_mut() {
            let to_middle = row[middle];
            if to_middle == INF {
                continue;
            }
            for (cell, &via) in row.iter_mut().zip(&through) {
                if to_middle + via < *cell {
                    *cell = to_middle + via;
                }
            }
        }
    }
    let mut best_city = 0;
    let mut best_count = n + 1;
    for (city, row) in dist.iter().enumerate() {
        let count = row
            .iter()
            .enumerate()
            .filter(|&(other, &distance)| other != city && distance <= distance_threshold)
            .count();
        // `<=` lets a later city win a tie.
        if count <= best_count {
            best_city = city;
            best_count = count;
        }
    }
    best_city as i32
}
