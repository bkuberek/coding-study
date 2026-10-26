# Product Except Self: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) besides the output | n is tiny, or as a correctness oracle |
| prefix-suffix-arrays | intermediate | O(n) | O(n) | first linear solution; easiest to explain |
| running-products | optimal | O(n) | O(1) besides the output | default answer; the follow-up asks for it |

Every approach uses the same split: `answer[i] = (product of everything left of i) * (product of everything right of i)`. They differ in whether those partial products are recomputed, stored, or carried along.

## Approach: brute-force (Multiply all other elements for each position)

### Intuition

Follow the definition: for each position, multiply every other element.

### Algorithm

1. For each position `i`:
   1. Set `product = 1`.
   2. For each position `j != i`, multiply `product` by `nums[j]`.
   3. Store `answer[i] = product`.
2. Return `answer`.

### Correctness

For each `i`, the inner loop multiplies exactly the elements at positions other than `i`, once each, which is the definition of `answer[i]`. Multiplication of integers is commutative and associative, so the order does not matter.

### Complexity

- Time: O(n^2) — n positions, each with n - 1 multiplications, at every input.
- Space: O(1) besides the output — one running product.

### Trade-offs

Trivially correct, so it is the oracle, but at n = 10,000 it already performs 10^8 multiplications. It recomputes almost the same product n times: the products for positions `i` and `i + 1` share all but two factors, which is exactly the reuse the linear approaches exploit.

### Pitfalls and edge cases

- Computing the total product once and dividing by `nums[i]` is forbidden here, and it fails on zeros anyway.
- Zeros need no special handling in a pure multiplication approach.

### Language notes

- Python: the reference multiplies `islice(nums, i)` and `islice(nums, i + 1, None)` with `math.prod`. Both run in C and copy nothing, so the memory stays O(1); slicing with `nums[:i]` would copy.
- Kotlin: `IntArray(n) { i -> ... }` builds the output with an initializer lambda; the last expression of the lambda is the element.

## Approach: prefix-suffix-arrays (Prefix and suffix product arrays)

### Intuition

Let `left[i]` be the product of `nums[0..i-1]` and `right[i]` the product of `nums[i+1..n-1]`. Each array follows from its neighbor with one multiplication: `left[i] = left[i - 1] * nums[i - 1]`. Two linear passes compute both arrays, and `answer[i] = left[i] * right[i]`.

### Algorithm

1. `left[0] = 1`; for `i` from 1 to n - 1, `left[i] = left[i - 1] * nums[i - 1]`.
2. `right[n - 1] = 1`; for `i` from n - 2 down to 0, `right[i] = right[i + 1] * nums[i + 1]`.
3. For each `i`, `answer[i] = left[i] * right[i]`.

### Correctness

By induction, `left[i]` is the product of the first `i` elements: it holds for `i = 0` (the empty product, 1), and step 1 extends the product of `nums[0..i-2]` by `nums[i-1]`. Symmetrically, `right[i]` is the product of `nums[i+1..n-1]`. Their product multiplies every element except `nums[i]`, exactly once each.

### Complexity

- Time: O(n) — three linear passes.
- Space: O(n) — the two helper arrays, besides the output.

### Trade-offs

The clearest linear solution, and the one to present first. It allocates two extra arrays, which the next approach removes. With every subset product guaranteed to fit in 32 bits, the intermediate products never overflow in Java or Kotlin either.

### Pitfalls and edge cases

- Off-by-one in the recurrences: `left[i]` must use `nums[i - 1]`, not `nums[i]`, or position `i` multiplies itself in.
- Initialize the borders with 1, the empty product. Java `new int[n]` starts with zeros, so `left[0]` and `right[n - 1]` must be set explicitly.

### Language notes

- Python: `[1] * n` creates the arrays; the final `zip` pairs `left` with `right`.
- TypeScript: `new Array<number>(n).fill(1)`, then `left.map((before, i) => before * right[i])`.
- Kotlin: `IntArray(n) { 1 }` fills with ones; `downTo` writes the backward loop.

## Approach: running-products (Prefix products in the output and a running suffix)

### Intuition

The output array has room for one number per position, so the left products can live there directly. The right products are only ever needed in order from the back, so a single variable can carry the current one while a second pass walks backwards and multiplies it in.

### Algorithm

1. `answer[0] = 1`; for `i` from 1 to n - 1, `answer[i] = answer[i - 1] * nums[i - 1]`.
2. Set `after = 1`.
3. For `i` from n - 1 down to 0:
   1. `answer[i] = answer[i] * after`.
   2. `after = after * nums[i]`.
4. Return `answer`.

### Correctness

After step 1, `answer[i]` is the product of `nums[0..i-1]`, by the same induction as `left`. Invariant of step 3: when position `i` is processed, `after` is the product of `nums[i+1..n-1]`. It holds at `i = n - 1` (empty product), and step 3.2 extends it by `nums[i]` before moving to `i - 1`. So step 3.1 turns `answer[i]` into left product times right product, which is the required value.

### Complexity

- Time: O(n) — two linear passes.
- Space: O(1) besides the output — one extra variable; the left products reuse the output array.

### Trade-offs

Same time as the two-array version with no extra memory, which is what the follow-up asks for. It is slightly harder to read because `answer` holds a different quantity during the first and the second pass; naming the running variable (`after`) and commenting the invariant helps in an interview.

### Pitfalls and edge cases

- Update `after` after using it, not before; swapping steps 3.1 and 3.2 multiplies `nums[i]` into its own answer.
- Zeros need no special case: a zero to the left of `i` makes the stored prefix zero, a zero to the right makes `after` zero.
- In JavaScript, `0 * -3` is `-0`. It compares equal to `0` and `JSON.stringify(-0)` prints `0`, so it is harmless here, but `Object.is(-0, 0)` is `false`.

### Language notes

- Python: integers never overflow, so the code needs no care about the 32-bit guarantee.
- TypeScript: `number` is a double; every product here is below 2^31, far inside the exactly representable range of 2^53.
- Java: `new int[n]` is zero-filled, hence the explicit `answer[0] = 1`; `answer[i] *= after` is ordinary `int` arithmetic, safe because every subset product fits in 32 bits.
- Kotlin: `IntArray(n) { 1 }` starts with ones, so the first pass can begin at index 1 with no extra assignment.
