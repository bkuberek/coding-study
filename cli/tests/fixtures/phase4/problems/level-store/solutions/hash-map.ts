export class LevelStore {
  private readonly values = new Map<string, string>();

  put(key: string, value: string): void {
    this.values.set(key, value);
  }

  get(key: string): string {
    return this.values.get(key) ?? "";
  }

  remove(key: string): boolean {
    return this.values.delete(key);
  }

  size(): number {
    return this.values.size;
  }

  keysWithPrefix(prefix: string): string[] {
    return [...this.values.keys()].filter((key) => key.startsWith(prefix)).sort();
  }
}
