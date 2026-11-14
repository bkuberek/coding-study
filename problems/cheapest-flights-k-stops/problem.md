# Cheapest Flights Within K Stops

## Statement

There are `n` cities, numbered `0` to `n - 1`, and a list of one-way flights: `flights[i] = [from, to, price]` is a flight from city `from` to city `to` that costs `price`. You want to travel from city `src` to city `dst`, but you accept at most `k` stops on the way, that is, at most `k + 1` flights in total. A stop is any city strictly between `src` and `dst` on your trip; passing through the same city twice counts twice.

Return the lowest total price of such a trip, or `-1` if no trip with at most `k` stops exists.

Reference: this is our own wording of LeetCode problem 787, [Cheapest Flights Within K Stops](https://leetcode.com/problems/cheapest-flights-within-k-stops/).

## Input

- `n`: the number of cities.
- `flights`: the flights, each `[from, to, price]`.
- `src`: the city where the trip starts.
- `dst`: the city where the trip must end.
- `k`: the most stops allowed.

## Output

The cheapest total price of a trip from `src` to `dst` that uses at most `k + 1` flights, or `-1`.

## Examples

### Example 1

<!-- case: ex1 -->

With at most one stop, the trips are `0 -> 1 -> 3` for 100 and the direct flight `0 -> 3` for 200. The cheaper trip `0 -> 2 -> 1 -> 3` for 80 needs two stops, so it is not allowed: the answer is 100.

### Example 2

<!-- case: ex2 -->

The same flights with two stops allowed: now `0 -> 2 -> 1 -> 3` for 20 + 10 + 50 = 80 is the cheapest trip.

## Constraints

- `1 <= n <= 1000`
- `0 <= flights.length <= 10^4`
- `0 <= from, to < n`, `from != to`, and no pair `(from, to)` appears twice.
- `1 <= price <= 10^4`
- `0 <= src, dst < n` and `src != dst`
- `0 <= k < n`

## Follow-ups

- Return the itinerary itself, not only its price.
- Why does plain Dijkstra on cities alone give wrong answers here?
- What if the limit were on the total travel time instead of the number of stops?

## Hints

### Hint 1

Without the stop limit this is a shortest-path problem. With the limit, the cheapest price depends on how many flights you have used, so it helps to track both.

### Hint 2

Let `best[i][c]` be the cheapest price to reach city `c` with at most `i` flights. Then `best[i][c]` comes from `best[i - 1][from] + price` over the flights into `c`.

### Hint 3

You only ever need the previous row. Run `k + 1` rounds of relaxing every flight, each round reading prices from a copy made before the round, so a single round never chains two flights.
