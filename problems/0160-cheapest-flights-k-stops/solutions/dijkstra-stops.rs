use std::cmp::Reverse;
use std::collections::BinaryHeap;

pub fn find_cheapest_price(n: i32, flights: Vec<Vec<i32>>, src: i32, dst: i32, k: i32) -> i32 {
    let mut graph: Vec<Vec<(usize, i32)>> = vec![Vec::new(); n as usize];
    for flight in &flights {
        graph[flight[0] as usize].push((flight[1] as usize, flight[2]));
    }
    // fewest[c] is the fewest flights with which c was settled so far. States are popped in
    // order of price, so a later state for c is useful only if it used fewer flights.
    let mut fewest = vec![k + 2; n as usize];
    // `BinaryHeap` is a max-heap, so `Reverse` makes the cheapest state pop first.
    let mut heap = BinaryHeap::new();
    heap.push(Reverse((0, src as usize, 0)));
    while let Some(Reverse((price, city, used))) = heap.pop() {
        if city == dst as usize {
            return price;
        }
        if used >= fewest[city] {
            continue;
        }
        fewest[city] = used;
        if used == k + 1 {
            continue; // no flights left
        }
        for &(neighbor, cost) in &graph[city] {
            heap.push(Reverse((price + cost, neighbor, used + 1)));
        }
    }
    -1
}
