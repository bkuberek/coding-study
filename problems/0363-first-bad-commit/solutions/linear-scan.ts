const GOOD = 0;
const BAD = 1;

export function firstBadCommit(statuses: number[]): number[] {
  let lastGood = -1;
  for (let position = 0; position < statuses.length; position++) {
    if (statuses[position] === GOOD) {
      lastGood = position;
    } else if (statuses[position] === BAD) {
      return [lastGood + 1, position];
    }
  }
  throw new Error("the history has no bad commit");
}
