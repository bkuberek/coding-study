// Labels for stock counts, imported by the entry module.

const SEPARATOR = ": ";

export function labelFor(name: string, count: number): string {
  return `${name}${SEPARATOR}${count}`;
}
