export function myPow(x: number, n: number): number {
  const base = n >= 0 ? x : 1 / x;
  let remaining = Math.abs(n);
  let result = 1;
  let done = 0;
  while (done < remaining) {
    result *= base;
    done++;
    if (result === 1) {
      // base^done == 1, so the powers repeat with period done (x = 1 or x = -1).
      remaining = (remaining - done) % done;
      done = 0;
    } else if (result === 0 || !Number.isFinite(result)) {
      break; // further multiplications cannot change the result
    }
  }
  return result;
}
