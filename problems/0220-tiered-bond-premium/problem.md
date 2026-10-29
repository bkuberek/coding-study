# Tiered Bond Premium

## Statement

A surety prices a contractor's performance bond from the contract price, using bands. Each band has a floor and a rate per 1,000 of price, and a rate applies only to the part of the price that lies inside its band: with floors 0 and 100,000, a 150,000 contract pays the first rate on 100,000 and the second rate on the remaining 50,000.

Band `i` runs from `bandFloors[i]` up to, but not including, `bandFloors[i + 1]`; the last band has no upper end. Nothing is charged for the part of the price below the first floor.

The charge of a band is the slice of the price inside it times its rate, divided by 1,000. Add the charges exactly and round the total once to cents, half up (a tie such as `0.005` goes to `0.01`).

## Input

- `contractPrice`: the price of the contract being bonded
- `bandFloors`: the lower end of each band, strictly ascending
- `ratesPerThousand`: `ratesPerThousand[i]` is the rate of band `i`, per 1,000 of price

## Output

The premium as a decimal, rounded to cents. Decimals are compared by value, so `11000.00` and `11000` are the same answer.

## Examples

### Example 1

<!-- case: ex1 -->

The price falls in the third band. The first 100,000 pays 25 per 1,000 (2,500), the next 400,000 pays 15 (6,000), and the remaining 250,000 pays 10 (2,500): 11,000 in total.

### Example 2

<!-- case: ex2 -->

The price sits exactly on the floor of the third band. That band gets an empty slice, so only the first two bands are charged: 2,500 + 6,000 = 8,500.

### Example 3

<!-- case: ex3 -->

The price reaches the open-ended top band: 2,500 + 6,000 + 20,000 on the middle bands, plus 500,000 at 7.5 per 1,000 (3,750), which is 32,250.

## Constraints

- `1 <= bandFloors.length == ratesPerThousand.length <= 20`.
- Floors are strictly ascending, `0 <= bandFloors[i] <= 10^10`, with at most 2 fractional digits.
- `0 <= ratesPerThousand[i] < 1000`, with at most 4 fractional digits.
- `0 <= contractPrice <= 10^10`, with at most 2 fractional digits.

## Follow-ups

- Add a minimum premium: how does it interact with the single final rounding?
- A step schedule, where the whole price pays the rate of the band it falls in. What jump does it create at each floor, and why is the banded version fairer?
- One table prices many bonds: precompute the total charge at each floor and binary-search the price's band.

## Hints

### Hint 1

For each band, how much of the price falls inside it?

### Hint 2

Keep every charge exact and round only the total.
