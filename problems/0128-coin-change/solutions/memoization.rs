const NOT_COMPUTED: i32 = -1;
// Larger than any real answer, small enough that 1 + INFINITY cannot overflow.
const INFINITY: i32 = 1 << 30;

/// The fewest coins that pay `remaining` exactly; `INFINITY` when it cannot be paid.
fn fewest(remaining: usize, coins: &[i32], memo: &mut [i32]) -> i32 {
    if remaining == 0 {
        return 0;
    }
    if memo[remaining] == NOT_COMPUTED {
        let mut best = INFINITY;
        for &coin in coins {
            if coin as usize <= remaining {
                best = best.min(1 + fewest(remaining - coin as usize, coins, memo));
            }
        }
        memo[remaining] = best;
    }
    memo[remaining]
}

pub fn coin_change(coins: Vec<i32>, amount: i32) -> i32 {
    let amount = amount as usize;
    let mut memo = vec![NOT_COMPUTED; amount + 1];
    let answer = fewest(amount, &coins, &mut memo);
    if answer >= INFINITY {
        -1
    } else {
        answer
    }
}
