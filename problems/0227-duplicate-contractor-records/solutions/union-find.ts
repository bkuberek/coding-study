const LEGAL_FORMS = new Set(["co", "company", "corp", "inc", "incorporated", "llc", "ltd"]);
const TAX_ID_DIGITS = 9;

function normalizeName(name: string): string {
  const words = name
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((word) => word.length > 0);
  while (words.length > 0 && LEGAL_FORMS.has(words[words.length - 1])) {
    words.pop();
  }
  return words.join(" ");
}

function normalizeTaxId(taxId: string): string {
  const digits = taxId.replace(/[^0-9]/g, "");
  return digits.length === TAX_ID_DIGITS ? digits : "";
}

export function duplicateGroups(names: string[], taxIds: string[]): number[][] {
  const parent = names.map((_, record) => record);
  const find = (record: number): number => {
    let current = record;
    while (parent[current] !== current) {
      parent[current] = parent[parent[current]]; // path halving
      current = parent[current];
    }
    return current;
  };

  const firstWithKey = new Map<string, number>();
  names.forEach((name, record) => {
    // The prefixes keep names and tax ids in separate key spaces.
    for (const key of [`name:${normalizeName(name)}`, `tax:${normalizeTaxId(taxIds[record])}`]) {
      if (key.endsWith(":")) {
        continue; // an empty key matches nothing
      }
      const first = firstWithKey.get(key);
      if (first === undefined) {
        firstWithKey.set(key, record);
      } else {
        parent[find(record)] = find(first);
      }
    }
  });

  const groups = new Map<number, number[]>(); // insertion order = smallest index first
  names.forEach((_, record) => {
    const root = find(record);
    const members = groups.get(root);
    if (members === undefined) {
      groups.set(root, [record]);
    } else {
      members.push(record);
    }
  });
  return [...groups.values()].filter((members) => members.length > 1);
}
