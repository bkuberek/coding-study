export function waitFor(value: number): number {
  while (value < 0) {
    // Spins forever: the CLI hang guard must stop it.
  }
  return value;
}
