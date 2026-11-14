export function kClosest(points: number[][], k: number): number[][] {
  // Squared distances order points exactly like distances, without square roots.
  const squared = ([x, y]: number[]): number => x * x + y * y;
  return [...points].sort((a, b) => squared(a) - squared(b)).slice(0, k);
}
