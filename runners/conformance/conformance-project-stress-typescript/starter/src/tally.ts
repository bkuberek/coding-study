export class Tally {
  async add(_key: string, _amount: number): Promise<number> {
    throw new Error("Not implemented");
  }

  count(_key: string): number {
    throw new Error("Not implemented");
  }
}
