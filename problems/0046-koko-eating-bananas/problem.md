# Koko Eating Bananas

## Statement

Koko has `n` piles of bananas in front of her; pile `i` holds `piles[i]` bananas. The keepers will be back in `h` hours, and she wants every banana gone by then.

She eats at a fixed integer speed of `k` bananas per hour, chosen once in advance. Each hour she picks a single pile that still has bananas and eats `k` of them. If the pile has fewer than `k` left, she finishes it and spends the rest of that hour idle: she never moves on to a second pile within the same hour. A pile of `p` bananas therefore takes `ceil(p / k)` hours.

Koko likes to eat slowly. Return the smallest speed `k` that lets her finish all piles within `h` hours.

Reference: this is our own wording of LeetCode problem 875, [Koko Eating Bananas](https://leetcode.com/problems/koko-eating-bananas/).

## Input

- `piles`: the number of bananas in each pile
- `h`: the number of hours available

## Output

The minimum positive integer `k` such that the sum of `ceil(piles[i] / k)` over all piles is at most `h`.

## Examples

### Example 1

<!-- case: ex1 -->

At speed 5 the piles take 1, 3, 2 and 2 hours, 8 in total, which is too many for 7 hours. At speed 6 they take 1, 2, 2 and 2 hours, exactly 7. So 6 is the slowest speed that works.

### Example 2

<!-- case: ex2 -->

There are as many hours as piles, so every pile must be finished in a single hour, and the largest pile, 30, sets the speed.

## Constraints

- `1 <= piles.length <= 10^4`
- `piles.length <= h <= 10^9`
- `1 <= piles[i] <= 10^9`

## Follow-ups

- Trying speeds one by one can take up to `max(piles)` attempts. How few attempts do you need if you exploit the fact that a faster speed never needs more hours?
- What are the tightest lower and upper bounds for the answer before you start searching?

## Hints

### Hint 1

Write a helper that, for a given speed, returns how many hours all piles take. How does its result change as the speed grows?

### Hint 2

The hours never increase when the speed increases. So the speeds split into "too slow" ones followed by "fast enough" ones, and you want the first fast-enough speed.

### Hint 3

Binary search the speed between 1 and the largest pile. The total hours can exceed the 32-bit range at slow speeds; use a 64-bit counter.
