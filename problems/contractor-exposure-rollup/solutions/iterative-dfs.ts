import { Decimal } from "#support";

interface Frame {
  node: string;
  next: number; // index of the next child to look at
}

export function totalExposure(
  edges: string[][],
  contractors: string[],
  exposures: Decimal[],
  root: string,
): Decimal {
  const children = new Map<string, string[]>();
  for (const [parent, child] of edges) {
    const list = children.get(parent);
    if (list === undefined) {
      children.set(parent, [child]);
    } else {
      list.push(child);
    }
  }
  const own = new Map<string, Decimal>();
  contractors.forEach((name, i) => own.set(name, exposures[i]));
  const zero = new Decimal(0);
  const onPath = new Set<string>([root]); // meeting one again closes a cycle
  const finished = new Set<string>(); // fully explored contractors, already counted
  let total = own.get(root) ?? zero;
  const stack: Frame[] = [{ node: root, next: 0 }];
  while (stack.length > 0) {
    const frame = stack[stack.length - 1];
    const below = children.get(frame.node) ?? [];
    if (frame.next === below.length) {
      stack.pop();
      onPath.delete(frame.node);
      finished.add(frame.node);
      continue;
    }
    const child = below[frame.next];
    frame.next += 1;
    if (onPath.has(child)) {
      return new Decimal(-1);
    }
    if (!finished.has(child)) {
      onPath.add(child);
      total = total.plus(own.get(child) ?? zero);
      stack.push({ node: child, next: 0 });
    }
  }
  return total;
}
