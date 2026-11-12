const BAD = 1;
const SKIP = 2;

export function firstBadCommit(statuses: number[]): number[] {
  const firstBad = findFirstBad(statuses);
  const lastGood = findLastGoodBefore(statuses, firstBad);
  return [lastGood + 1, firstBad];
}

function findFirstBad(statuses: number[]): number {
  // Some commit is bad, so the first bad commit is somewhere in [low, high].
  let low = 0;
  let high = statuses.length - 1;
  while (low < high) {
    const middle = (low + high) >>> 1;
    let probe = middle;
    while (probe >= low && statuses[probe] === SKIP) {
      probe--;
    }
    if (probe >= low && statuses[probe] === BAD) {
      high = probe;
    } else {
      low = middle + 1;
    }
  }
  return low;
}

function findLastGoodBefore(statuses: number[], firstBad: number): number {
  // Before the first bad commit every commit that was tested is good. The last good one is
  // somewhere in [low, high], where -1 stands for "none".
  let low = -1;
  let high = firstBad - 1;
  while (low < high) {
    const middle = (low + high + 1) >> 1;
    let probe = middle;
    while (probe <= high && statuses[probe] === SKIP) {
      probe++;
    }
    if (probe <= high) {
      low = probe;
    } else {
      high = middle - 1;
    }
  }
  return low;
}
