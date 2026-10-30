# Cheapest Flights Within K Stops: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| bellman-ford | optimal | O(k·E) | O(n) | default answer: the hop limit is exactly what its rounds count |
| dijkstra-stops | intermediate | O(k·E·log(k·E)) | O(k·E) | the cheapest trip is usually found early, or many queries share a small k |

At most `k` stops means at most `k + 1` flights. The limit breaks plain Dijkstra on cities: the cheapest way to reach a city may use too many flights to continue from there, while a pricier way with fewer flights still can. Both approaches make the number of flights part of the computation. E is the number of flights.

## Approach: bellman-ford (Bellman-Ford limited to k + 1 rounds)

### Intuition

Bellman-Ford's rounds have a precise meaning: after round `i`, every city holds the cheapest price among trips of at most `i` flights, provided each round only extends trips that existed before it. So run exactly `k + 1` rounds, and in each one relax every flight using prices copied from the end of the previous round. That copy is the whole trick: without it, one round could chain several flights and break the count.

### Algorithm

1. Set `price[src] = 0` and every other price to infinity.
2. Repeat `k + 1` times (stop early if a round changes nothing):
   1. Copy `price` into `previous`.
   2. For every flight `[from, to, cost]`, set `price[to] = min(price[to], previous[from] + cost)`.
3. Return `price[dst]`, or -1 if it is infinite.

### Correctness

This is the dynamic program `best[i][c] = min(best[i - 1][c], min over flights into c of best[i - 1][from] + cost)`, where `best[i][c]` is the cheapest price of a trip from `src` to `c` with at most `i` flights; `previous` is row `i - 1` and `price` becomes row `i`. By induction on `i` each row is exact: a cheapest trip with at most `i` flights either uses at most `i - 1` flights, or ends with a flight whose start is reached cheaply with at most `i - 1` flights. After `k + 1` rounds, `price[dst]` is the cheapest trip with at most `k` stops. A round without changes means every later row would equal this one, so stopping early is safe.

### Complexity

- Time: O(k·E) — `k + 1` rounds, each relaxing every flight once; copying the array adds O(k·n), which is within O(k·E) when every city has a flight and small anyway.
- Space: O(n) — two arrays of prices; the DP keeps only the previous row.

### Trade-offs

Short, exact, and its bound depends on `k`, not on prices. It always relaxes every flight in every round, even far from the destination; when the cheapest trip uses few flights and `k` is large, a priority-driven search can finish sooner, but with no better worst case.

### Pitfalls and edge cases

- Relax from the copy, never from the array being updated: updating in place lets a single round use two flights, which counts stops wrong.
- `k + 1` rounds, not `k`: the limit is on stops, and a trip with `k` stops has `k + 1` flights.
- Guard against adding to "infinity" with fixed-size integers.

### Language notes

- Python: `price[:]` copies the row; `math.inf` marks unreachable cities.
- TypeScript: `previous.slice()` copies the row; `Infinity + cost` stays `Infinity`, so no guard is needed.
- Java: `price.clone()` copies the row, and `Integer.MAX_VALUE` must be checked before adding to avoid overflow.
- Kotlin: `copyOf()` copies the `IntArray`, and `for ((start, end, cost) in flights)` destructures each flight.
- Go: `slices.Clone(price)` copies the row. `math.MaxInt` marks an unreachable city, and the `!= unreached` check before the addition is required: `MaxInt + cost` wraps to a negative number instead of failing, and would pass the `<` test.
- Rust: `price.clone()` copies the `Vec<i32>`. `i32::MAX` marks an unreachable city; the build checks overflow, so adding a cost to it would panic, and the `!= UNREACHED` guard is what prevents that. `0..=k` runs the `k + 1` rounds.

## Approach: dijkstra-stops (Dijkstra over (city, flights taken) states)

### Intuition

Make the state `(city, flights used)` and run Dijkstra on states, so the first time the destination comes off the heap, its price is the cheapest among all allowed trips. Most states are useless: once a city has been taken off the heap with some number of flights, a later (hence more expensive) arrival is only interesting if it used fewer flights, because only then can it still go farther. Keeping the fewest flights per city prunes everything else.

### Algorithm

1. Build adjacency lists and push `(0, src, 0)` onto a min-heap ordered by price.
2. While the heap is not empty, pop `(price, city, used)`:
   1. If `city == dst`, return `price`.
   2. If `used` is not smaller than `fewest[city]`, skip it; otherwise set `fewest[city] = used`.
   3. If `used < k + 1`, push `(price + cost, neighbor, used + 1)` for every flight out of `city`.
3. Return -1.

### Correctness

States leave the heap in non-decreasing order of price, and every pushed state is a real trip with at most `k + 1` flights. When a state `(c, u)` is skipped, an earlier state `(c, u')` with `u' <= u` and a price no higher was already expanded; any continuation of the skipped trip is also available from that state, with no more flights and no higher price, so no cheaper trip to `dst` is lost. Therefore the first destination state popped is the cheapest allowed trip; if the heap empties, there is none.

### Complexity

- Time: O(k·E·log(k·E)) — each city is expanded at most `k + 2` times (its `fewest` value strictly drops each time), each expansion pushes one state per outgoing flight, and each heap operation costs O(log(k·E)).
- Space: O(k·E) — the heap can hold that many states in the worst case.

### Trade-offs

Often fast in practice, because it stops as soon as the destination is popped, and it extends naturally to other constraints on the state. Its worst case is a log factor slower than Bellman-Ford's and it needs a priority queue, so in an interview the limited Bellman-Ford is the cleaner answer.

### Pitfalls and edge cases

- Pruning by cheapest price per city, as plain Dijkstra does, is wrong here; prune by fewest flights, which is the dimension that still matters after a pop.
- Check the destination when it is popped, not when it is pushed; only a popped state is known to be cheapest.
- Do not expand a state that already used `k + 1` flights.

### Language notes

- Python: `heapq` with `(price, city, used)` tuples, which compare by price first.
- TypeScript: the reference implements a small binary min-heap over `[price, city, used]` tuples, since there is no built-in priority queue.
- Java: `PriorityQueue<int[]>` ordered by `state[0]`.
- Kotlin: `PriorityQueue<Triple<Int, Int, Int>>(compareBy { it.first })`; the popped `Triple` destructures into `price`, `city` and `used`.
- Go: `container/heap` has no ready-made queue; the reference defines `stateHeap` with `Len`, `Less`, `Swap`, `Push` and `Pop`, and `heap.Push` / `heap.Pop` do the sifting. `Push` and `Pop` take a pointer receiver because they change the slice's length.
- Rust: `BinaryHeap` is a max-heap, so entries are wrapped in `Reverse` to pop the cheapest first. The `(price, city, used)` tuple orders lexicographically, like Python's, and `while let Some(Reverse((price, city, used))) = heap.pop()` destructures the popped state.
