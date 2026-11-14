# Reconstruct Itinerary

## Statement

You found a pile of one-way plane tickets, `tickets[i] = [from, to]`, all belonging to one traveler, and you know the trip started at the airport `"JFK"`. The traveler used every ticket exactly once, each ticket departing from the airport where the previous flight landed. Airports are written as three uppercase letters, and the same ticket (same `from` and `to`) may appear more than once.

Rebuild the itinerary: the list of airports in the order visited, starting with `"JFK"`. Several orders may use all tickets; return the one that comes first in dictionary order when the airport lists are compared element by element.

Reference: this is our own wording of LeetCode problem 332, [Reconstruct Itinerary](https://leetcode.com/problems/reconstruct-itinerary/).

## Input

- `tickets`: the tickets, each `[from, to]`.

## Output

The airports of the trip in order, `tickets.length + 1` of them, starting at `"JFK"` and using every ticket exactly once; among all such trips, the lexicographically smallest one.

## Examples

### Example 1

<!-- case: ex1 -->

From `JFK` the smaller destination is `ATL`, but no ticket leaves `ATL`, so flying there first would strand the traveler with tickets left over. The trip must go `JFK`, `SFO`, `LAX`, back to `JFK`, and end in `ATL`.

### Example 2

<!-- case: ex2 -->

Both orders use every ticket; flying to `AUS` first is smaller than flying to `BOS` first, because `"AUS" < "BOS"`.

## Constraints

- `1 <= tickets.length <= 1000`
- Every airport is three uppercase English letters, and `from != to` on every ticket.
- The tickets form at least one trip that starts at `"JFK"` and uses all of them.

## Follow-ups

- How would you check whether such a trip exists at all, before searching for one?
- What if the start airport were not given?
- Your solution recurses once per ticket. How do you make it iterative for very long trips?

## Hints

### Hint 1

Taking the smallest destination every time is right most of the time. When does it fail, and what does the traveler's position look like when it fails?

### Hint 2

The trip is an Eulerian path: it uses every edge of a directed multigraph exactly once. Hierholzer's algorithm builds one by walking until stuck and splicing in detours.

### Hint 3

Walk greedily along the smallest unused ticket, and append an airport to the answer only when it has no unused tickets left. The answer then comes out in reverse.
