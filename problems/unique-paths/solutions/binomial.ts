// Products of two residues reach 10^18, beyond 2^53, so the arithmetic uses BigInt.
const MOD = 1_000_000_007n;

function power(base: bigint, exponent: bigint): bigint {
  let result = 1n;
  let factor = base % MOD;
  for (let rest = exponent; rest > 0n; rest >>= 1n) {
    if ((rest & 1n) === 1n) {
      result = (result * factor) % MOD;
    }
    factor = (factor * factor) % MOD;
  }
  return result;
}

export function uniquePaths(m: number, n: number): number {
  // A route is a sequence of m + n - 2 moves; choose which of them are the shorter direction.
  const moves = BigInt(m + n - 2);
  const chosen = BigInt(Math.min(m, n) - 1);
  let numerator = 1n;
  let denominator = 1n;
  for (let step = 1n; step <= chosen; step++) {
    numerator = (numerator * (moves - chosen + step)) % MOD;
    denominator = (denominator * step) % MOD;
  }
  // MOD is prime, so denominator^(MOD - 2) is its inverse (Fermat's little theorem).
  return Number((numerator * power(denominator, MOD - 2n)) % MOD);
}
