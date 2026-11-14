# Reconstruct Itinerary: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| backtracking | brute | O(E^d) | O(E) | small inputs, or as the first idea to refine in an interview |
| hierholzer | optimal | O(E·log E) | O(E) | default answer |

Airports are nodes and tickets are directed edges of a multigraph; a trip that uses every ticket once is an Eulerian path starting at `JFK`. The problem asks for the lexicographically smallest one. E is the number of tickets and d the largest number of tickets leaving one airport. Greedily taking the smallest destination almost works; the two approaches differ in how they repair the cases where it does not.

## Approach: backtracking (Try destinations in order and backtrack from dead ends)

### Intuition

Build the trip one flight at a time, always trying the destinations of the current airport in alphabetical order. If the traveler gets stuck with tickets left over, undo the last flight and try the next destination. Because the choices are tried in alphabetical order, the first complete trip found is the smallest one.

### Algorithm

1. Sort each airport's destinations alphabetically and give every ticket a "used" flag.
2. `extend(airport)`: if the route already has `E + 1` airports, succeed. Otherwise, for each unused ticket from `airport` in order (skipping a ticket identical to one just tried and undone), mark it used, append its destination, and recurse; on failure, undo both and continue. Fail if no ticket works.
3. Start with route `[JFK]` and call `extend("JFK")`.

### Correctness

The search explores all ways to order the tickets as a trip from `JFK`, in lexicographic order of the resulting airport sequence, because at each position it tries the possible next airports from smallest to largest and fully explores each before the next. The first complete trip it reaches is therefore the smallest. Skipping a ticket identical to one just tried is safe: identical tickets are interchangeable, so the second attempt would explore exactly the same trips. A trip exists by the constraints, so the search succeeds.

### Complexity

- Time: O(E^d) — in the worst case the search may retry many orderings of the tickets out of each airport; on typical inputs dead ends are rare and shallow, and the run is close to the O(E·log E) cost of sorting.
- Space: O(E) — the route, the flags, and a recursion as deep as the trip.

### Trade-offs

Easy to explain and to get right, and its order of exploration gives the lexicographic answer for free. Its worst case is exponential, which an interviewer will point out; Hierholzer's algorithm removes the need to undo anything. The recursion is as deep as the number of tickets, which is fine up to the constraint of 1000.

### Pitfalls and edge cases

- Sort destinations once, up front; sorting inside the recursion multiplies the cost.
- Undo both the flag and the route entry on failure.
- Identical tickets must each be used once; track them per ticket, not per destination name.

### Language notes

- Python: `sorted(tickets)` orders tickets by origin, then destination, so each airport's list is already in order when built.
- TypeScript: the default `sort()` compares UTF-16 code units, which orders uppercase codes correctly; the recursive helper is a closure over the maps and the route.
- Java: the state lives in fields that are reset at the start of each call, keeping the recursive method's signature small; `List.of()` stands in for airports with no outgoing tickets.
- Kotlin: `groupBy({ it[0] }, { it[1] })` builds the destination lists in one call, and `mapValues` sorts them.
- Go: `extend` is a closure that calls itself, so it is declared first with `var extend func(airport string) bool` and assigned afterwards. `slices.Sort` orders each destination list in place, and the `route = route[:len(route)-1]` re-slice is the undo step that Python spells `route.pop()`. Go has no `defaultdict`, but a missing key reads as a nil slice, so the loop over an airport with no tickets simply does nothing.
- Rust: a recursive closure is awkward under the borrow checker, so the search state (the destination lists with a used flag per ticket, the route and the ticket count) lives in a `Search` struct and `extend` is a `&mut self` method. The strings are `&str` borrowed from `tickets`, so nothing is cloned until the final `String::from` conversion. Sorting the `(destination, used)` pairs sorts by destination because every flag starts `false`.

## Approach: hierholzer (Hierholzer's algorithm with sorted destinations)

### Intuition

Walk greedily: from the current airport always take the smallest unused ticket. When the walk gets stuck, the airport where it is stuck must be the end of the whole trip (or the end of a detour that the trip must take before continuing). So emit stuck airports in reverse order: an airport is appended to the answer only when it has no unused tickets left, then the walk backs up to the previous airport and continues from there. Reversing the emitted list gives the trip, and the greedy choices make it the smallest.

### Algorithm

1. For each airport, keep its destinations so that the smallest unused one can be taken quickly (a sorted list popped from the end, or a min-heap).
2. Push `JFK` on a stack. While the stack is not empty: if the airport on top has an unused ticket, take the smallest one and push its destination; otherwise pop the airport and append it to `route`.
3. Return `route` reversed.

### Correctness

Every ticket is used exactly once, since it is removed when taken. An airport is appended only after all its outgoing tickets are used, and each detour that a stuck walk forces is emitted before the airport it branches from, which is exactly the splicing step of Hierholzer's algorithm; so the reversed output is an Eulerian path from `JFK`. Lexicographic minimality: at each airport the walk takes the smallest destination first; if that choice leads into a part of the graph that must be finished last, the walk gets stuck there, and the reversal places that part at the end, after the larger choices, which is the only order in which a valid trip can use it. Any trip that took a larger destination earlier where a smaller one was possible would compare larger at that position.

### Complexity

- Time: O(E·log E) — sorting (or heap operations on) the destinations; the walk itself pushes and pops each airport visit once.
- Space: O(E) — the destination lists, the stack and the route.

### Trade-offs

Linear apart from sorting, no backtracking, and short. The iterative stack avoids recursion depth limits on long trips. The correctness argument is subtler than the backtracking one, so be ready to explain why stuck airports go last.

### Pitfalls and edge cases

- Append an airport only when it has no tickets left, not when you first visit it.
- Reverse the route at the end (or prepend while building it).
- Taking destinations in increasing order is what makes the result smallest; any other order still gives a valid trip, but not the required one.

### Language notes

- Python: destinations sorted in reverse, so `list.pop()` from the end removes the smallest in O(1).
- TypeScript: each destination list is sorted and reversed once, then used as a stack with `pop()`.
- Java: a `PriorityQueue<String>` per airport gives the smallest destination with `poll()`; `LinkedList.addFirst` builds the route already in order.
- Kotlin: the same `PriorityQueue` per airport; a `kotlin.collections.ArrayDeque` serves both as the stack and, with `addFirst`, as the route.
- Go: the stack is a slice, and "pop" is `stack[:len(stack)-1]`. Each destination list is sorted and then reversed with `slices.Reverse`, so its last element is the smallest destination and shrinking the slice by one removes it in O(1).
- Rust: `Vec::pop` on the reverse-sorted list takes the smallest destination, and `destinations.get_mut(airport).and_then(Vec::pop)` folds "no entry" and "empty list" into one `None`. `stack.last()` is copied out with `Some(&airport)` before `stack.push`, so the borrow has ended when the stack changes.
