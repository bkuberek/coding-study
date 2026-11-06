function row(group: number[], probabilities: number[], outcomes: boolean[], binCount: number): number[] {
  if (group.length === 0) {
    return [0, 0, 0];
  }
  const probabilitySums = new Array<number>(binCount).fill(0);
  const trueCounts = new Array<number>(binCount).fill(0);
  let squaredError = 0;
  for (const index of group) {
    const probability = probabilities[index];
    const y = outcomes[index] ? 1 : 0;
    const bin = Math.min(Math.floor(probability * binCount), binCount - 1);
    probabilitySums[bin] += probability;
    trueCounts[bin] += y;
    squaredError += (probability - y) ** 2;
  }
  // (bin size / N) * |sum / bin size - trues / bin size| is |sum - trues| / N: the bin size
  // cancels, so an empty bin needs no special case.
  let gaps = 0;
  for (let bin = 0; bin < binCount; bin += 1) {
    gaps += Math.abs(probabilitySums[bin] - trueCounts[bin]);
  }
  return [group.length, gaps / group.length, squaredError / group.length];
}

export function calibrationReport(
  probabilities: number[],
  outcomes: boolean[],
  sliceNames: string[],
  reportSlices: string[],
  binCount: number,
): number[][] {
  const bySlice = new Map<string, number[]>();
  sliceNames.forEach((name, index) => {
    const members = bySlice.get(name);
    if (members === undefined) {
      bySlice.set(name, [index]);
    } else {
      members.push(index);
    }
  });
  const everyone = probabilities.map((_, index) => index);
  return [
    row(everyone, probabilities, outcomes, binCount),
    ...reportSlices.map((name) => row(bySlice.get(name) ?? [], probabilities, outcomes, binCount)),
  ];
}
